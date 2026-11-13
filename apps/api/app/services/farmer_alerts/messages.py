"""Brief, predictable messages for a farmer's chosen language.

A deterministic local-language summary is preferred over ungrounded machine
translation. Long scientific evidence stays available in the app; notifications
are intended as prompts, not remote agronomic prescriptions.
"""
from __future__ import annotations
from datetime import date
from typing import Any

HEADINGS = {
    "en": {"calendar": "Your crop calendar", "weather": "Weather to review", "science": "Farm model update"},
    "hi": {"calendar": "आपका फसल कैलेंडर", "weather": "मौसम की जानकारी", "science": "खेती के मॉडल की सूचना"},
    "kn": {"calendar": "ನಿಮ್ಮ ಬೆಳೆ ಕ್ಯಾಲೆಂಡರ್", "weather": "ಹವಾಮಾನ ಮಾಹಿತಿ", "science": "ಕೃಷಿ ಮಾದರಿ ಮಾಹಿತಿ"},
}
TEXT = {
    "en": {
        "calendar": "Check the planting date or crop activity in your farm plan.",
        "weather": "The weather forecast needs a review. Check the field before changing a decision.",
        "science": "Your simulation suggests water stress. Check the crop and soil before irrigating.",
        "view": "Open TerraPulse for the details and source.",
        "estimated": "This is an estimate, not a field observation.",
    },
    "hi": {
        "calendar": "अपनी फसल योजना में बुवाई की तारीख या अगला काम देखें।",
        "weather": "मौसम का पूर्वानुमान देखें। कोई निर्णय बदलने से पहले खेत की स्थिति जाँचें।",
        "science": "मॉडल में पानी का तनाव दिखता है। सिंचाई से पहले फसल और मिट्टी जाँचें।",
        "view": "कारण और स्रोत देखने के लिए TerraPulse खोलें।",
        "estimated": "यह अनुमान है, खेत में किया गया मापन नहीं।",
    },
    "kn": {
        "calendar": "ನಿಮ್ಮ ಕೃಷಿ ಯೋಜನೆಯಲ್ಲಿ ಬಿತ್ತನೆ ದಿನಾಂಕ ಅಥವಾ ಮುಂದಿನ ಕೆಲಸ ನೋಡಿ.",
        "weather": "ಹವಾಮಾನ ಮುನ್ಸೂಚನೆಯನ್ನು ಪರಿಶೀಲಿಸಿ. ನಿರ್ಧಾರ ಬದಲಿಸುವ ಮೊದಲು ಹೊಲವನ್ನು ನೋಡಿ.",
        "science": "ಮಾದರಿಯಲ್ಲಿ ನೀರಿನ ಒತ್ತಡ ಕಂಡುಬಂದಿದೆ. ನೀರಾವರಿಗೆ ಮೊದಲು ಬೆಳೆ ಮತ್ತು ಮಣ್ಣನ್ನು ಪರಿಶೀಲಿಸಿ.",
        "view": "ವಿವರಗಳು ಮತ್ತು ಮೂಲಕ್ಕಾಗಿ TerraPulse ತೆರೆಯಿರಿ.",
        "estimated": "ಇದು ಅಂದಾಜು; ಹೊಲದ ನೇರ ಅಳತೆ ಅಲ್ಲ.",
    },
}


def render(event: dict[str, Any], locale: str = "en") -> str:
    locale = locale if locale in TEXT else "en"
    category = event.get("category", "calendar")
    if category not in TEXT[locale]:
        raise ValueError("Unsupported alert category")
    crop = str(event.get("cropName") or "your crop")[:80]
    event_date = str(event.get("eventDate") or "")
    try:
        event_date = date.fromisoformat(event_date).strftime("%d %b %Y")
    except ValueError:
        event_date = ""
    # Keep model sources and specific milestone titles visible without inventing a translation.
    title = str(event.get("title") or "")[:130]
    lines = ["🌱 TerraPulse · " + HEADINGS[locale][category], f"🌾 {crop}" + (f" · {event_date}" if event_date else "")]
    if title:
        # Retain the specific event title even when a sourced local-language
        # translation is not supplied; never omit what actually happened.
        lines.append(title)
    lines.append(TEXT[locale][category])
    if category != "calendar":
        lines.append(TEXT[locale]["estimated"])
    lines.append(TEXT[locale]["view"])
    return "\n".join(lines)[:1600]
