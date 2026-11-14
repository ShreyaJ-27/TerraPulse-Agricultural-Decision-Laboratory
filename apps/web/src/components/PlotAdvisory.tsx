import { useState } from "react";
import { Locale, translations } from "../i18n";
import { AnalysisResult, apiClient } from "../services/apiClient";
import { useSpeechInput } from "./interaction";
import { ErrorState } from "./ui";

export function PlotAdvisory({ farmId, plotId, locale }: {
  farmId: string;
  plotId: string;
  locale: Locale;
}) {
  const copy = translations[locale];
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<AnalysisResult>();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const speech = useSpeechInput(locale, copy, setQuestion);

  async function ask() {
    if (busy || !question.trim()) return;
    setBusy(true);
    setError("");
    setAnswer(undefined);
    try {
      setAnswer(await apiClient.analyzeFarm({
        farmId,
        plotId,
        language: locale,
        question: question.trim(),
        includeWeather: true,
        includeSoil: true,
        includeCrop: true,
        includeSimulation: true,
        includeComparison: true,
      }));
    } catch {
      setError(copy.analysisError);
    } finally {
      setBusy(false);
    }
  }

  return <>
    <form className="advisory-ask-bar" onSubmit={(event) => { event.preventDefault(); void ask(); }}>
      <input
        className="advisory-input"
        aria-label={copy.questionPrompt}
        placeholder="Ask about this plot’s weather, soil or scientific results"
        value={question}
        onChange={(event) => setQuestion(event.target.value)}
        maxLength={2000}
        required
      />
      <button type="button" className="advisory-send-btn" onClick={speech.toggle} aria-pressed={speech.listening}>
        {speech.listening ? copy.stopListening : <>🎙 {copy.speakQuestion}</>}
      </button>
      <button type="submit" className="advisory-send-btn" disabled={busy || !question.trim()}>
        {busy ? copy.analysisLoading : copy.askButton}
      </button>
    </form>
    <p className="advisory-voice-status" role="status">
      {speech.notice || (speech.listening ? copy.listeningButton : speech.supported ? copy.voiceReady : copy.micUnavailable)}
    </p>
    {error && <ErrorState label={error} />}
    {answer && <article className="advisory-answer-card" aria-live="polite">
      <p>{answer.summary}</p>
      <small>{answer.generationMode === "llm" ? copy.llmGenerated
        : answer.generationMode === "deterministic_fallback" ? copy.fallbackGenerated : copy.deterministicGenerated}</small>
      {answer.sections.map((section) => <section key={section.key}>
        <h3>{section.title}</h3>
        <p>{section.content}</p>
        {section.claims.length > 0 && <ul>{section.claims.map((claim) => <li key={claim.claimId}>
          {claim.metric}: {claim.value} {claim.unit} · {claim.sourceField}
        </li>)}</ul>}
      </section>)}
      {answer.escalations.map((item) => <p key={item.category}>{item.recommendedAction}</p>)}
    </article>}
  </>;
}
