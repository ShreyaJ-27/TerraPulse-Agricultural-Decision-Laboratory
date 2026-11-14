from __future__ import annotations

import os
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access import authorize_path_farm
from app.core.db import get_session
from app.schemas import ApiResponse
from app.services.farmer_alerts.models import FarmerAlert, TelegramDelivery, TelegramSubscription

router = APIRouter(prefix="/api/v1/notifications", tags=["farmer-notifications"],
                   dependencies=[Depends(authorize_path_farm)])


@router.get("/farms/{farm_id}", response_model=ApiResponse)
async def list_farm_notifications(
    farm_id: UUID,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ApiResponse:
    alerts = list(
        (
            await session.scalars(
                select(FarmerAlert)
                .where(FarmerAlert.farm_id == farm_id)
                .order_by(desc(FarmerAlert.created_at))
            )
        ).all()
    )

    deliveries = list(
        (
            await session.scalars(
                select(TelegramDelivery)
                .join(FarmerAlert, TelegramDelivery.alert_id == FarmerAlert.id)
                .where(FarmerAlert.farm_id == farm_id)
            )
        ).all()
    )
    delivery_map = {d.alert_id: d for d in deliveries}

    results = []
    for alert in alerts:
        deliv = delivery_map.get(alert.id)
        results.append(
            {
                "id": str(alert.id),
                "farmId": str(alert.farm_id),
                "plotId": str(alert.plot_id),
                "category": alert.category,
                "kind": alert.kind,
                "eventDate": alert.event_date.isoformat(),
                "payload": alert.payload,
                "createdAt": alert.created_at.isoformat() if alert.created_at else None,
                "delivery": {
                    "status": deliv.status if deliv else "delivered_in_app",
                    "attempts": deliv.attempts if deliv else 1,
                    "channel": "Telegram & In-App" if deliv else "In-App",
                    "telegramMessageId": deliv.telegram_message_id if deliv else None,
                    "updatedAt": deliv.updated_at.isoformat() if deliv and deliv.updated_at else None,
                },
            }
        )

    return ApiResponse(
        data={"farmId": str(farm_id), "notifications": results, "total": len(results)},
        correlationId=request.state.correlation_id,
    )


@router.get("/telegram/status/{farm_id}", response_model=ApiResponse)
async def get_telegram_status(
    farm_id: UUID,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ApiResponse:
    subs = list(
        (
            await session.scalars(
                select(TelegramSubscription).where(TelegramSubscription.farm_id == farm_id)
            )
        ).all()
    )
    bot_username = os.environ.get("TELEGRAM_BOT_USERNAME", "").lstrip("@")
    return ApiResponse(
        data={
            "farmId": str(farm_id),
            "connected": len(subs) > 0 and any(s.active for s in subs),
            "botUsername": bot_username,
            "subscriptionCount": len(subs),
            "subscriptions": [
                {
                    "id": str(s.id),
                    "active": s.active,
                    "locale": s.locale,
                    "categories": s.categories,
                    "timezone": s.timezone,
                    "quietHours": f"{s.quiet_start_hour}:00 - {s.quiet_end_hour}:00",
                }
                for s in subs
            ],
        },
        correlationId=request.state.correlation_id,
    )


@router.get("/deliveries/{farm_id}", response_model=ApiResponse)
async def list_deliveries(
    farm_id: UUID,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ApiResponse:
    deliveries = list(
        (
            await session.scalars(
                select(TelegramDelivery)
                .join(FarmerAlert, TelegramDelivery.alert_id == FarmerAlert.id)
                .where(FarmerAlert.farm_id == farm_id)
                .order_by(desc(TelegramDelivery.updated_at))
                .limit(50)
            )
        ).all()
    )

    return ApiResponse(
        data={
            "farmId": str(farm_id),
            "deliveries": [
                {
                    "deliveryId": str(d.id),
                    "alertId": str(d.alert_id),
                    "subscriptionId": str(d.subscription_id),
                    "status": d.status,
                    "attempts": d.attempts,
                    "telegramMessageId": d.telegram_message_id,
                    "lastError": d.last_error,
                    "updatedAt": d.updated_at.isoformat() if d.updated_at else None,
                }
                for d in deliveries
            ],
            "total": len(deliveries),
        },
        correlationId=request.state.correlation_id,
    )
