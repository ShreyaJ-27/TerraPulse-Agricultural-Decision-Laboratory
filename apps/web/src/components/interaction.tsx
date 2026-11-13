import { FormEvent, useEffect, useRef, useState } from "react";
import { Locale, Translation } from "../i18n";
import { apiClient, CropInteraction } from "../services/apiClient";
import { ErrorState, LoadingState, PageContainer } from "./ui";

const DEMO_PROMPTS: Record<Locale, string[]> = {
  en: [
    "I grow turmeric. Can you predict yield?",
    "How much water does ragi need?",
    "My crop has brown spots.",
    "What is today's turmeric market price?",
  ],
  kn: [
    "ನನ್ನ ಬೆಳೆ ಅರಿಶಿನ.",
    "ಅರಿಶಿನ ಬೆಳೆಗೆ ಇಳುವರಿ ಮುನ್ಸೂಚನೆ ಇದೆಯೇ?",
    "ರಾಗಿ ಬೆಳೆಗೆ ಎಷ್ಟು ನೀರು ಬೇಕು?",
    "ಬೆಳೆಯಲ್ಲಿ ಕೀಟ ಮತ್ತು ರೋಗ ಬಾಧೆ ಹೆಚ್ಚಾಗಿದೆ.",
    "ಅರಿಶಿನ ಮಾರುಕಟ್ಟೆ ಬೆಲೆ ಎಷ್ಟು?",
  ],
  hi: [
    "मेरी फसल हल्दी है।",
    "क्या हल्दी की उपज का अनुमान मिलेगा?",
    "रागी के लिए कितना पानी चाहिए?",
    "फसल में कीड़े लग गए हैं।",
    "हल्दी का मंडी भाव क्या है?",
  ],
};

interface SpeechRecognitionEvent {
  results: { [index: number]: { [index: number]: { transcript: string } } };
}

interface SpeechRecognitionErrorEvent {
  error: string;
  message?: string;
}

interface ISpeechRecognition {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  onstart: (() => void) | null;
  onresult: ((event: SpeechRecognitionEvent) => void) | null;
  onerror: ((event: SpeechRecognitionErrorEvent) => void) | null;
  onend: (() => void) | null;
  start: () => void;
  stop: () => void;
  abort: () => void;
}

type SpeechUtteranceInstance = {
  lang: string;
  voice: unknown;
  onstart: (() => void) | null;
  onend: (() => void) | null;
  onerror: (() => void) | null;
};

type WindowWithSpeech = typeof window & {
  SpeechRecognition?: new () => ISpeechRecognition;
  webkitSpeechRecognition?: new () => ISpeechRecognition;
  SpeechSynthesisUtterance?: new (text?: string) => SpeechUtteranceInstance;
};

export function FarmerInteraction({
  copy,
  locale,
}: {
  copy: Translation;
  locale: Locale;
}) {
  const [query, setQuery] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [interaction, setInteraction] = useState<CropInteraction | null>(null);

  // Speech-to-Text State
  const [isListening, setIsListening] = useState(false);
  const [sttSupported, setSttSupported] = useState(false);
  const [sttNotice, setSttNotice] = useState("");
  const recognitionRef = useRef<ISpeechRecognition | null>(null);

  // Text-to-Speech State
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [ttsNotice, setTtsNotice] = useState("");

  useEffect(() => {
    // Check Web Speech API support
    const win = window as unknown as WindowWithSpeech;
    const SpeechConstructor = win.SpeechRecognition || win.webkitSpeechRecognition;
    setSttSupported(Boolean(SpeechConstructor));

    const handleVoicesChanged = () => {
      if (typeof window !== "undefined" && "speechSynthesis" in window) {
        window.speechSynthesis.getVoices();
      }
    };
    if (typeof window !== "undefined" && "speechSynthesis" in window) {
      window.speechSynthesis.addEventListener("voiceschanged", handleVoicesChanged);
    }

    return () => {
      if (typeof window !== "undefined" && "speechSynthesis" in window) {
        window.speechSynthesis.removeEventListener("voiceschanged", handleVoicesChanged);
        window.speechSynthesis.cancel();
      }
      // Cleanup recognition on unmount
      if (recognitionRef.current) {
        try {
          recognitionRef.current.abort();
        } catch {
          // ignore
        }
      }
    };
  }, []);

  const executeQuery = async (queryText: string) => {
    const text = queryText.trim();
    if (!text) return;

    setBusy(true);
    setError("");
    setTtsNotice("");
    if (typeof window !== "undefined" && "speechSynthesis" in window) {
      window.speechSynthesis.cancel();
      setIsSpeaking(false);
    }

    try {
      const result = await apiClient.interactCrop({
        query: text,
        language: locale,
      });
      setInteraction(result);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Interaction request failed";
      setError(msg);
    } finally {
      setBusy(false);
    }
  };

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    executeQuery(query);
  };

  const handleChipClick = (prompt: string) => {
    setQuery(prompt);
    executeQuery(prompt);
  };

  const toggleListening = () => {
    setSttNotice("");
    if (isListening) {
      if (recognitionRef.current) {
        recognitionRef.current.stop();
      }
      setIsListening(false);
      return;
    }

    const win = window as unknown as WindowWithSpeech;
    const SpeechConstructor = win.SpeechRecognition || win.webkitSpeechRecognition;
    if (!SpeechConstructor) {
      setSttNotice(copy.micUnavailable);
      return;
    }

    try {
      const recognition = new SpeechConstructor();
      recognition.lang = locale === "kn" ? "kn-IN" : locale === "hi" ? "hi-IN" : "en-IN";
      recognition.continuous = false;
      recognition.interimResults = false;

      recognition.onstart = () => {
        setIsListening(true);
        setSttNotice("");
      };

      recognition.onresult = (event: SpeechRecognitionEvent) => {
        const transcript = event.results[0]?.[0]?.transcript || "";
        if (transcript) {
          setQuery(transcript);
          executeQuery(transcript);
        }
      };

      recognition.onerror = (event: SpeechRecognitionErrorEvent) => {
        setIsListening(false);
        if (event.error === "not-allowed" || event.error === "permission-denied") {
          setSttNotice(copy.micPermissionDenied);
        } else if (event.error === "no-speech") {
          setSttNotice("No speech detected. Please try again.");
        } else {
          setSttNotice(copy.speechError);
        }
      };

      recognition.onend = () => {
        setIsListening(false);
      };

      recognitionRef.current = recognition;
      recognition.start();
    } catch {
      setIsListening(false);
      setSttNotice(copy.speechError);
    }
  };

  const playSpeech = () => {
    setTtsNotice("");
    if (typeof window === "undefined" || !("speechSynthesis" in window)) {
      setTtsNotice("Speech synthesis is not supported by this browser.");
      return;
    }

    if (isSpeaking) {
      window.speechSynthesis.cancel();
      setIsSpeaking(false);
      return;
    }

    const textToSpeak = interaction?.speechText || interaction?.responseText;
    if (!textToSpeak) return;

    window.speechSynthesis.cancel();
    const win = window as unknown as WindowWithSpeech;
    if (!win.SpeechSynthesisUtterance) {
      setTtsNotice("Speech synthesis utterance is not supported.");
      return;
    }
    const utterance = new win.SpeechSynthesisUtterance(textToSpeak);
    const targetLang = locale === "kn" ? "kn-IN" : locale === "hi" ? "hi-IN" : "en-IN";
    utterance.lang = targetLang;

    // Check if a voice matching the target language is available
    const voices = window.speechSynthesis.getVoices();
    const matchingVoice = voices.find((v) => {
      const vLang = v.lang.toLowerCase().replace("_", "-");
      return vLang.startsWith(targetLang.toLowerCase()) || vLang.startsWith(locale.toLowerCase());
    });

    if (matchingVoice) {
      utterance.voice = matchingVoice;
    } else if (locale !== "en") {
      // Gracefully notify that an OS/browser language voice pack is required
      setTtsNotice(copy.ttsUnavailable);
      return;
    }

    utterance.onstart = () => setIsSpeaking(true);
    utterance.onend = () => setIsSpeaking(false);
    utterance.onerror = () => {
      setIsSpeaking(false);
      setTtsNotice("Audio playback failed or was interrupted.");
    };

    window.speechSynthesis.speak(utterance);
  };

  const resetInteraction = () => {
    setQuery("");
    setInteraction(null);
    setError("");
    setSttNotice("");
    setTtsNotice("");
    if (typeof window !== "undefined" && "speechSynthesis" in window) {
      window.speechSynthesis.cancel();
      setIsSpeaking(false);
    }
  };

  return (
    <PageContainer>
      <div className="page-intro">
        <p className="eyebrow">
          Issue #22 · Local Language & Speech Interaction ·{" "}
          <span style={{ color: sttSupported ? "#24533b" : "#7a8f80" }}>
            {sttSupported ? "Voice ready" : "Text/Touch mode"}
          </span>
        </p>
        <h2>{copy.interactionTitle}</h2>
        <p>{copy.interactionSubtitle}</p>
      </div>

      <div className="interaction-workspace" style={{ maxWidth: 840, margin: "0 auto" }}>
        {/* Input & Voice Controls */}
        <div className="form-panel" style={{ padding: "24px 28px", borderRadius: 8 }}>
          <form onSubmit={handleSubmit} style={{ display: "grid", gap: 16 }}>
            <label style={{ display: "grid", gap: 8, fontSize: 14 }}>
              <span>{copy.interactionPlaceholder}</span>
              <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                <input
                  type="text"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder={copy.interactionPlaceholder}
                  disabled={busy}
                  style={{ flex: 1, fontSize: 16, padding: "12px 14px" }}
                  aria-label="Farmer query input"
                />

                {/* Speech-to-Text Button */}
                <button
                  type="button"
                  onClick={toggleListening}
                  className={isListening ? "primary-button" : "secondary-button"}
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: 6,
                    padding: "12px 16px",
                    background: isListening ? "#b84232" : undefined,
                    borderColor: isListening ? "#b84232" : undefined,
                  }}
                  title={isListening ? "Stop listening" : "Click to speak with microphone"}
                  aria-label={isListening ? "Listening with microphone" : "Speak question"}
                >
                  <span aria-hidden="true" style={{ fontSize: 18 }}>
                    {isListening ? "⏹" : "🎙"}
                  </span>
                  <span>{isListening ? copy.listeningButton : "Voice"}</span>
                </button>

                {/* Submit Button */}
                <button
                  type="submit"
                  disabled={busy || !query.trim()}
                  className="primary-button"
                  style={{ padding: "12px 20px" }}
                >
                  <span>{copy.askButton}</span>
                </button>
              </div>
            </label>
          </form>

          {/* Voice Notices / Fallback Messages */}
          {sttNotice && (
            <p className="warning" style={{ margin: "8px 0 0", fontSize: 13 }} role="status">
              {sttNotice}
            </p>
          )}

          {/* Suggested Prompts */}
          <div style={{ marginTop: 16 }}>
            <p style={{ margin: "0 0 8px", fontSize: 12, color: "#62796b", fontWeight: 600 }}>
              {copy.suggestedPrompts} ({copy.language}: {locale.toUpperCase()}):
            </p>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
              {DEMO_PROMPTS[locale].map((prompt, idx) => (
                <button
                  key={idx}
                  type="button"
                  className="secondary-button"
                  onClick={() => handleChipClick(prompt)}
                  disabled={busy}
                  style={{
                    fontSize: 12,
                    padding: "6px 12px",
                    borderRadius: 16,
                    border: "1px solid #c7d8ca",
                    background: "#f4f8f3",
                    color: "#24533b",
                    textAlign: "left",
                  }}
                >
                  {prompt}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Loading State */}
        {busy && (
          <div style={{ margin: "32px 0" }}>
            <LoadingState label={copy.loading} />
          </div>
        )}

        {/* Error State */}
        {error && (
          <div style={{ margin: "24px 0" }}>
            <ErrorState label={error} />
          </div>
        )}

        {/* Results Area */}
        {interaction && !busy && (
          <article
            className="info-card"
            style={{
              marginTop: 24,
              padding: 28,
              borderRadius: 8,
              background: "#ffffff",
              border: "1px solid #dbe2d8",
              boxShadow: "0 4px 18px rgba(36, 83, 59, 0.06)",
              display: "grid",
              gap: 20,
            }}
          >
            {/* Header: Intent & Locale */}
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "1px solid #eef2ed", paddingBottom: 12 }}>
              <div>
                <span
                  style={{
                    padding: "4px 10px",
                    borderRadius: 4,
                    background: interaction.escalationRequired ? "#fbeae8" : "#e8f2e9",
                    color: interaction.escalationRequired ? "#a02e20" : "#24533b",
                    font: "600 11px 'DM Mono', monospace",
                    textTransform: "uppercase",
                  }}
                >
                  {interaction.intent}
                </span>
                <span style={{ marginLeft: 10, fontSize: 12, color: "#7a8f80" }}>
                  Resolution: <strong>{interaction.resolutionStatus}</strong>
                </span>
              </div>

              {/* Text-to-Speech Controls */}
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <button
                  type="button"
                  onClick={playSpeech}
                  className="secondary-button"
                  style={{
                    padding: "6px 14px",
                    fontSize: 12,
                    display: "inline-flex",
                    alignItems: "center",
                    gap: 6,
                    background: isSpeaking ? "#eef6ef" : undefined,
                    borderColor: isSpeaking ? "#24533b" : undefined,
                  }}
                >
                  <span aria-hidden="true">{isSpeaking ? "⏹" : "🔊"}</span>
                  <span>{isSpeaking ? copy.ttsStopButton : copy.ttsButton}</span>
                </button>
              </div>
            </div>

            {ttsNotice && (
              <p className="warning" style={{ margin: 0, fontSize: 12 }} role="status">
                {ttsNotice}
              </p>
            )}

            {/* Resolved Crop Card (if exact match) */}
            {interaction.resolvedCrop && (
              <div
                style={{
                  background: "#f4f8f3",
                  border: "1px solid #d2e4d4",
                  borderRadius: 6,
                  padding: "14px 18px",
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                }}
              >
                <div>
                  <h4 style={{ margin: 0, fontSize: 16, color: "#1c3c2c" }}>
                    {interaction.resolvedCrop.canonicalName}{" "}
                    <small style={{ color: "#5a7a67", fontStyle: "italic", fontSize: 13 }}>
                      ({interaction.resolvedCrop.scientificName})
                    </small>
                  </h4>
                  <p style={{ margin: "4px 0 0", fontSize: 12, color: "#546e5e" }}>
                    {interaction.resolvedCrop.family && (
                      <>Family: <strong>{interaction.resolvedCrop.family}</strong> · </>
                    )}
                    {interaction.resolvedCrop.selectedEngine && (
                      <>Selected Engine: <strong>{interaction.resolvedCrop.selectedEngine}</strong> ({interaction.resolvedCrop.engineVersion || "1.0"})</>
                    )}
                  </p>
                </div>
              </div>
            )}

            {/* Ambiguous Candidates List */}
            {interaction.candidates && interaction.candidates.length > 0 && interaction.resolutionStatus === "ambiguous" && (
              <div style={{ background: "#fbf8ef", border: "1px solid #eadcb7", borderRadius: 6, padding: "14px 18px" }}>
                <h4 style={{ margin: "0 0 10px", fontSize: 14, color: "#7a5c18" }}>
                  Ambiguous Crop — Please click the intended crop to confirm:
                </h4>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
                  {interaction.candidates.map((cand) => (
                    <button
                      key={cand.cropId}
                      type="button"
                      className="secondary-button"
                      onClick={() => handleChipClick(cand.canonicalName)}
                      style={{
                        padding: "8px 14px",
                        fontSize: 13,
                        background: "#fff",
                        borderColor: "#d8c48a",
                        color: "#6b5015",
                      }}
                    >
                      {cand.canonicalName} ({cand.scientificName}) <span>↗</span>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Main Response Text */}
            <div style={{ fontSize: 16, lineHeight: 1.6, color: "#1c342b", background: "#fbfcf9", padding: "18px 20px", borderRadius: 6, border: "1px solid #e6ece4" }}>
              <p style={{ margin: 0, whiteSpace: "pre-wrap" }}>{interaction.responseText}</p>
            </div>

            {/* Escalation Warning (if pathology / KVK referral) */}
            {interaction.escalationRequired && (
              <div
                style={{
                  background: "#fff3f1",
                  borderLeft: "4px solid #cb3b27",
                  padding: "16px 20px",
                  borderRadius: 4,
                }}
              >
                <h4 style={{ margin: "0 0 6px", color: "#9c2615", fontSize: 14 }}>
                  {copy.escalationTitle}
                </h4>
                <p style={{ margin: 0, fontSize: 13, color: "#8a2d1f", lineHeight: 1.5 }}>
                  TerraPulse restricts disease and chemical recommendations to prevent crop damage. Please seek in-person diagnostic support from an authorized agronomist or extension center.
                </p>
              </div>
            )}

            {/* Scientific Limitations Card */}
            {interaction.limitations && interaction.limitations.length > 0 && (
              <div style={{ background: "#f8f9f6", border: "1px solid #e1e7de", padding: "14px 18px", borderRadius: 6 }}>
                <h5 style={{ margin: "0 0 8px", fontSize: 12, textTransform: "uppercase", letterSpacing: "0.1em", color: "#667f6f" }}>
                  {copy.limitationsTitle}
                </h5>
                <ul style={{ margin: 0, paddingLeft: 20, fontSize: 13, color: "#546c5c", lineHeight: 1.5 }}>
                  {interaction.limitations.map((lim, index) => (
                    <li key={index}>{lim}</li>
                  ))}
                </ul>
              </div>
            )}

            {/* Sources & Citations */}
            {interaction.sources && interaction.sources.length > 0 && (
              <div style={{ fontSize: 12, color: "#718979", borderTop: "1px solid #eef2ed", paddingTop: 12 }}>
                <strong>{copy.sourcesTitle}:</strong> {interaction.sources.join(" · ")}
              </div>
            )}

            {/* Action Bar */}
            <div style={{ display: "flex", justifyContent: "flex-end", paddingTop: 8 }}>
              <button
                type="button"
                className="secondary-button"
                onClick={resetInteraction}
                style={{ fontSize: 13, padding: "8px 16px" }}
              >
                {copy.askAnother}
              </button>
            </div>
          </article>
        )}
      </div>
    </PageContainer>
  );
}
