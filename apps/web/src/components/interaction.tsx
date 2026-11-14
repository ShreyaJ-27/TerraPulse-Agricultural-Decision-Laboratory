import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { Locale, Translation } from "../i18n";
import {
  AnalysisRequest,
  AnalysisResult,
  Branch,
  Comparison,
  CropInteraction,
  Farm,
  Simulation,
  apiClient,
} from "../services/apiClient";
import { EmptyState, ErrorState, LoadingState, PageContainer, ReusableCard } from "./ui";

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

const ANALYSIS_PROMPTS: Record<Locale, string[]> = {
  en: [
    "Explain the latest scientific result for this plot.",
    "Which environmental evidence supports this result?",
    "What information is missing or uncertain?",
  ],
  kn: [
    "ಈ ಹೊಲದ ಇತ್ತೀಚಿನ ವೈಜ್ಞಾನಿಕ ಫಲಿತಾಂಶವನ್ನು ವಿವರಿಸಿ.",
    "ಈ ಫಲಿತಾಂಶಕ್ಕೆ ಯಾವ ಪರಿಸರ ಸಾಕ್ಷ್ಯ ಬೆಂಬಲ ನೀಡುತ್ತದೆ?",
    "ಯಾವ ಮಾಹಿತಿ ಲಭ್ಯವಿಲ್ಲ ಅಥವಾ ಅನಿಶ್ಚಿತವಾಗಿದೆ?",
  ],
  hi: [
    "इस खेत के नवीनतम वैज्ञानिक परिणाम को समझाएं।",
    "इस परिणाम का समर्थन कौन-सा पर्यावरणीय साक्ष्य करता है?",
    "कौन-सी जानकारी उपलब्ध नहीं है या अनिश्चित है?",
  ],
};

const CROP_DISPLAY_NAMES: Record<string, Partial<Record<Locale, string>>> = {
  Turmeric: { kn: "ಅರಿಶಿನ", hi: "हल्दी" },
  Maize: { kn: "ಮೆಕ್ಕೆಜೋಳ", hi: "मक्का" },
  Wheat: { kn: "ಗೋಧಿ", hi: "गेहूँ" },
  Okra: { kn: "ಬೆಂಡೆಕಾಯಿ", hi: "भिंडी" },
  "Pearl Millet": { kn: "ಸಜ್ಜೆ", hi: "बाजरा" },
  "Finger Millet": { kn: "ರಾಗಿ", hi: "रागी" },
  "Foxtail Millet": { kn: "ನವಣೆ", hi: "कंगनी" },
  "Chickpea (Bengal Gram)": { kn: "ಕಡಲೆ", hi: "चना" },
  "Black Gram (Urad)": { kn: "ಉದ್ದು", hi: "उड़द" },
  "Upland Cotton": { kn: "ಹತ್ತಿ", hi: "कपास" },
};

function displayCropName(canonicalName: string, locale: Locale): string {
  return CROP_DISPLAY_NAMES[canonicalName]?.[locale] ?? canonicalName;
}

interface RecognitionResultEvent {
  results: { [index: number]: { [index: number]: { transcript: string } } };
}
interface RecognitionErrorEvent {
  error: string;
}
interface SpeechRecognitionInstance {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  onstart: (() => void) | null;
  onresult: ((event: RecognitionResultEvent) => void) | null;
  onerror: ((event: RecognitionErrorEvent) => void) | null;
  onend: (() => void) | null;
  start: () => void;
  stop: () => void;
  abort: () => void;
}
type BrowserSpeechWindow = typeof window & {
  SpeechRecognition?: new () => SpeechRecognitionInstance;
  webkitSpeechRecognition?: new () => SpeechRecognitionInstance;
};

export function useSpeechInput(
  locale: Locale,
  copy: Translation,
  onTranscript: (value: string) => void,
) {
  const [supported, setSupported] = useState(false);
  const [listening, setListening] = useState(false);
  const [notice, setNotice] = useState("");
  const recognitionRef = useRef<SpeechRecognitionInstance | null>(null);
  const mountedRef = useRef(false);

  useEffect(() => {
    mountedRef.current = true;
    const browserWindow = window as BrowserSpeechWindow;
    setSupported(Boolean(browserWindow.SpeechRecognition || browserWindow.webkitSpeechRecognition));
    return () => {
      mountedRef.current = false;
      try {
        recognitionRef.current?.abort();
      } catch {
        // The browser may already have stopped recognition.
      }
      recognitionRef.current = null;
    };
  }, []);

  useEffect(() => {
    if (!recognitionRef.current) return;
    try {
      recognitionRef.current.stop();
    } catch {
      recognitionRef.current.abort();
    }
    setListening(false);
  }, [locale]);

  const toggle = () => {
    setNotice("");
    if (recognitionRef.current) {
      try {
        recognitionRef.current?.stop();
      } catch {
        recognitionRef.current?.abort();
      }
      return;
    }
    const browserWindow = window as BrowserSpeechWindow;
    const SpeechRecognition =
      browserWindow.SpeechRecognition || browserWindow.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      setNotice(copy.micUnavailable);
      return;
    }
    try {
      const recognition = new SpeechRecognition();
      recognition.lang = locale === "kn" ? "kn-IN" : locale === "hi" ? "hi-IN" : "en-IN";
      recognition.continuous = false;
      recognition.interimResults = false;
      recognition.onstart = () => {
        if (mountedRef.current && recognitionRef.current === recognition) setListening(true);
      };
      recognition.onresult = (event) => {
        const transcript = event.results[0]?.[0]?.transcript?.trim();
        if (mountedRef.current && recognitionRef.current === recognition && transcript) onTranscript(transcript);
      };
      recognition.onerror = (event) => {
        if (!mountedRef.current || recognitionRef.current !== recognition) return;
        setListening(false);
        const errors: Record<string, string> = {
          "not-allowed": copy.micPermissionDenied,
          "permission-denied": copy.micPermissionDenied,
          "service-not-allowed": copy.micPermissionDenied,
          "audio-capture": copy.micUnavailable,
          "no-speech": copy.noSpeech,
          "language-not-supported": copy.recognitionLanguageUnsupported,
          network: copy.recognitionNetworkError,
          aborted: copy.recognitionInterrupted,
        };
        setNotice(errors[event.error] || copy.speechError);
      };
      recognition.onend = () => {
        if (recognitionRef.current !== recognition) return;
        recognitionRef.current = null;
        if (mountedRef.current) setListening(false);
      };
      recognitionRef.current = recognition;
      setListening(true);
      recognition.start();
    } catch {
      recognitionRef.current = null;
      setListening(false);
      setNotice(copy.speechError);
    }
  };
  return { supported, listening, notice, setNotice, toggle };
}

function useSpeechPlayback(locale: Locale, copy: Translation) {
  const [voices, setVoices] = useState<SpeechSynthesisVoice[]>([]);
  const [voicesReady, setVoicesReady] = useState(false);
  const [speaking, setSpeaking] = useState(false);
  const [notice, setNotice] = useState("");
  const currentUtterance = useRef<SpeechSynthesisUtterance | null>(null);
  const mountedRef = useRef(false);

  useEffect(() => {
    mountedRef.current = true;
    if (!("speechSynthesis" in window)) {
      setVoicesReady(true);
      return () => { mountedRef.current = false; };
    }
    const updateVoices = () => {
      const available = window.speechSynthesis.getVoices();
      setVoices(available);
      if (available.length) setVoicesReady(true);
    };
    updateVoices();
    window.speechSynthesis.addEventListener("voiceschanged", updateVoices);
    const timeout = window.setTimeout(() => setVoicesReady(true), 1200);
    return () => {
      mountedRef.current = false;
      window.clearTimeout(timeout);
      window.speechSynthesis.removeEventListener("voiceschanged", updateVoices);
      window.speechSynthesis.cancel();
    };
  }, []);

  useEffect(() => {
    if ("speechSynthesis" in window) window.speechSynthesis.cancel();
    setSpeaking(false);
    setNotice("");
  }, [locale]);

  const stop = () => {
    if ("speechSynthesis" in window) window.speechSynthesis.cancel();
    currentUtterance.current = null;
    setSpeaking(false);
  };

  const speak = (text: string) => {
    setNotice("");
    if (!("speechSynthesis" in window) || !window.SpeechSynthesisUtterance) {
      setNotice(copy.ttsUnavailable);
      return;
    }
    if (!voicesReady) {
      setNotice(copy.voiceLoading);
      return;
    }
    const targetLanguage = locale === "kn" ? "kn-IN" : locale === "hi" ? "hi-IN" : "en-IN";
    const voice = voices.find((candidate) => {
      const voiceLanguage = candidate.lang.toLowerCase().replace("_", "-");
      return voiceLanguage.startsWith(targetLanguage.toLowerCase())
        || voiceLanguage.startsWith(`${locale}-`);
    });
    if (!voice) {
      setNotice(copy.ttsUnavailable);
      return;
    }
    stop();
    const utterance = new window.SpeechSynthesisUtterance(text);
    utterance.lang = targetLanguage;
    utterance.voice = voice;
    utterance.onstart = () => {
      if (mountedRef.current && currentUtterance.current === utterance) setSpeaking(true);
    };
    utterance.onend = () => {
      if (mountedRef.current && currentUtterance.current === utterance) {
        setSpeaking(false);
        currentUtterance.current = null;
      }
    };
    utterance.onerror = () => {
      if (mountedRef.current && currentUtterance.current === utterance) {
        setSpeaking(false);
        setNotice(copy.playbackError);
        currentUtterance.current = null;
      }
    };
    currentUtterance.current = utterance;
    window.speechSynthesis.speak(utterance);
  };
  return { speaking, notice, setNotice, speak, stop };
}

export function FarmerInteraction({ copy, locale }: { copy: Translation; locale: Locale }) {
  const [query, setQuery] = useState("");
  const [interaction, setInteraction] = useState<CropInteraction | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const busyRef = useRef(false);
  const [analysisQuestion, setAnalysisQuestion] = useState("");
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null);
  const [analysisError, setAnalysisError] = useState("");
  const [analysisBusy, setAnalysisBusy] = useState(false);
  const analysisBusyRef = useRef(false);
  const [farms, setFarms] = useState<Farm[]>([]);
  const [farmId, setFarmId] = useState("");
  const [plotId, setPlotId] = useState("");
  const [branchId, setBranchId] = useState("");
  const [runId, setRunId] = useState("");
  const [comparisonId, setComparisonId] = useState("");
  const [branches, setBranches] = useState<Branch[]>([]);
  const [runs, setRuns] = useState<Simulation[]>([]);
  const [comparisons, setComparisons] = useState<Comparison[]>([]);
  const [farmLoadError, setFarmLoadError] = useState("");
  const [choiceLoadError, setChoiceLoadError] = useState("");
  const [choicesBusy, setChoicesBusy] = useState(false);
  const [lastAnalysisRequest, setLastAnalysisRequest] = useState<AnalysisRequest | null>(null);
  const [showEvidence, setShowEvidence] = useState(false);
  const analysisSpeech = useSpeechInput(locale, copy, setAnalysisQuestion);
  const cropSpeech = useSpeechInput(locale, copy, setQuery);
  const playback = useSpeechPlayback(locale, copy);

  useEffect(() => {
    let active = true;
    apiClient.listFarms()
      .then((response) => { if (active) setFarms(response.farms); })
      .catch(() => { if (active) setFarmLoadError(copy.analysisError); });
    return () => { active = false; };
  }, [copy.analysisError]);

  const selectedFarm = farms.find((farm) => farm.farmId === farmId);
  const plots = selectedFarm?.plots || [];
  const selectedPlot = plots.find((plot) => plot.plotId === plotId);
  const selectedComparison = comparisons.find((comparison) => comparison.comparisonId === comparisonId);
  const effectiveBranchId = selectedComparison?.baselineBranchId || branchId;
  const availableRuns = useMemo(
    () => runs.filter(
      (run) =>
        run.status === "completed"
        && (!effectiveBranchId || run.branchId === effectiveBranchId)
        && (!selectedComparison || run.simulationRunId === selectedComparison.baselineRunId),
    ),
    [runs, effectiveBranchId, selectedComparison],
  );
  const selectedRun = availableRuns.find((run) => run.simulationRunId === runId);

  useEffect(() => {
    if (!farmId || !plotId) return;
    let active = true;
    setChoicesBusy(true);
    setChoiceLoadError("");
    Promise.all([
      apiClient.listBranches(farmId, plotId),
      apiClient.listSimulations(farmId, plotId),
      apiClient.listComparisons(farmId, plotId),
    ])
      .then(([branchResponse, runResponse, comparisonResponse]) => {
        if (!active) return;
        setBranches(branchResponse.branches);
        setRuns(runResponse.simulations);
        setComparisons(comparisonResponse.comparisons);
      })
      .catch(() => { if (active) setChoiceLoadError(copy.analysisError); })
      .finally(() => { if (active) setChoicesBusy(false); });
    return () => { active = false; };
  }, [farmId, plotId, copy.analysisError]);

  useEffect(() => {
    if (runId && !availableRuns.some((run) => run.simulationRunId === runId)) setRunId("");
  }, [runId, availableRuns]);

  const stopPlayback = () => {
    playback.stop();
  };

  const submitCropQuestion = async (value: string) => {
    const text = value.trim();
    if (!text || busyRef.current) return;
    busyRef.current = true;
    setBusy(true);
    setError("");
    setInteraction(null);
    stopPlayback();
    try {
      setInteraction(await apiClient.interactCrop({ query: text, language: locale }));
    } catch {
      setError(copy.analysisError);
    } finally {
      busyRef.current = false;
      setBusy(false);
    }
  };

  const submitCropForm = (event: FormEvent) => {
    event.preventDefault();
    void submitCropQuestion(query);
  };

  const submitFarmAnalysis = async (request: AnalysisRequest) => {
    if (analysisBusyRef.current) return;
    analysisBusyRef.current = true;
    setAnalysisBusy(true);
    setAnalysisError("");
    setAnalysisResult(null);
    stopPlayback();
    setLastAnalysisRequest(request);
    try {
      setAnalysisResult(await apiClient.analyzeFarm(request));
    } catch {
      setAnalysisError(copy.analysisError);
    } finally {
      analysisBusyRef.current = false;
      setAnalysisBusy(false);
    }
  };

  const submitAnalysisForm = (event: FormEvent) => {
    event.preventDefault();
    if (!farmId || !plotId || !analysisQuestion.trim()) {
      setAnalysisError(copy.chooseFarmPlot);
      return;
    }
    const request: AnalysisRequest = {
      farmId,
      plotId,
      branchId: selectedComparison?.baselineBranchId || selectedRun?.branchId || branchId || undefined,
      comparisonBranchId: selectedComparison?.alternativeBranchId,
      comparisonId: selectedComparison?.comparisonId,
      simulationRunId: selectedRun?.simulationRunId,
      question: analysisQuestion.trim(),
      language: locale,
      includeWeather: true,
      includeSoil: true,
      includeCrop: true,
      includeSimulation: true,
      includeComparison: Boolean(selectedComparison),
    };
    void submitFarmAnalysis(request);
  };

  const selectFarm = (value: string) => {
    setFarmId(value);
    setPlotId("");
    setBranchId("");
    setRunId("");
    setComparisonId("");
    setBranches([]);
    setRuns([]);
    setComparisons([]);
    setAnalysisResult(null);
  };
  const selectPlot = (value: string) => {
    setPlotId(value);
    setBranchId("");
    setRunId("");
    setComparisonId("");
    setBranches([]);
    setRuns([]);
    setComparisons([]);
    setAnalysisResult(null);
  };
  const clearCropQuestion = () => {
    setQuery("");
    setInteraction(null);
    setError("");
    cropSpeech.setNotice("");
    stopPlayback();
  };
  const clearAnalysisQuestion = () => {
    setAnalysisQuestion("");
    setAnalysisResult(null);
    setAnalysisError("");
    analysisSpeech.setNotice("");
    setLastAnalysisRequest(null);
    stopPlayback();
  };

  const selectPrompt = (prompt: string) => {
    setQuery(prompt);
    void submitCropQuestion(prompt);
  };

  return (
    <PageContainer>
      <div className="page-intro">
        <p className="eyebrow">{copy.assisted}</p>
        <h2>{copy.interactionTitle}</h2>
        <p>{copy.interactionSubtitle}</p>
        <p className="warning" role="status">{copy.textMode}</p>
      </div>

      <section className="interaction-workspace" aria-labelledby="crop-help-heading">
        <ReusableCard>
          <div className="page-intro">
            <h3 id="crop-help-heading">{copy.cropHelpTitle}</h3>
            <p>{copy.cropHelpDescription}</p>
          </div>
          <form onSubmit={submitCropForm} className="form-panel">
            <label>
              <span>{copy.askUsingText}</span>
              <textarea
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder={copy.interactionPlaceholder}
                rows={3}
                disabled={busy}
                aria-label={copy.askUsingText}
              />
            </label>
            <div className="form-actions">
              <button type="button" className="secondary-button" onClick={cropSpeech.toggle}>
                {cropSpeech.listening ? copy.stopListening : copy.speakQuestion}
              </button>
              <button type="submit" className="primary-button" disabled={busy || !query.trim()}>
                {copy.askButton}
              </button>
              {(query || interaction || error) && (
                <button type="button" className="text-button" onClick={clearCropQuestion}>
                  {copy.newQuestion}
                </button>
              )}
            </div>
            <p className="warning" role="status">
              {cropSpeech.notice || (cropSpeech.supported ? copy.voiceReady : copy.micUnavailable)}
            </p>
          </form>
          <div className="prompt-list" aria-label={copy.suggestedPrompts}>
            {DEMO_PROMPTS[locale].map((prompt) => (
              <button
                key={prompt}
                type="button"
                className="secondary-button"
                disabled={busy}
                onClick={() => selectPrompt(prompt)}
              >
                {prompt}
              </button>
            ))}
          </div>
          {busy && <LoadingState label={copy.loading} />}
          {error && <ErrorState label={error} />}
          {interaction && (
            <article className="info-card" aria-live="polite">
              {interaction.resolvedCrop && (
                <h4>
                  {displayCropName(interaction.resolvedCrop.canonicalName, locale)}
                  {interaction.resolvedCrop.scientificName
                    ? ` (${interaction.resolvedCrop.scientificName})`
                    : ""}
                  {interaction.resolvedCrop.selectedEngine
                    ? ` · ${interaction.resolvedCrop.selectedEngine} ${interaction.resolvedCrop.engineVersion || ""}`
                    : ""}
                </h4>
              )}
              {interaction.candidates?.length ? (
                <div className="candidate-list">
                  <p>{interaction.responseText}</p>
                  {interaction.candidates.map((candidate) => (
                    <button
                      key={candidate.cropId}
                      type="button"
                      className="secondary-button"
                      onClick={() => selectPrompt(candidate.canonicalName)}
                    >
                      {displayCropName(candidate.canonicalName, locale)}
                      {candidate.scientificName ? ` · ${candidate.scientificName}` : ""}
                    </button>
                  ))}
                </div>
              ) : (
                <p>{interaction.responseText}</p>
              )}
              {interaction.escalationRequired && (
                <p className="warning" role="alert">{copy.escalationTitle}</p>
              )}
              {interaction.limitations.length > 0 && (
                <section>
                  <h4>{copy.limitationsTitle}</h4>
                  <ul>{interaction.limitations.map((item) => <li key={item}>{item}</li>)}</ul>
                </section>
              )}
              {interaction.sources.length > 0 && (
                <p><strong>{copy.sourcesTitle}:</strong> {interaction.sources.join(" · ")}</p>
              )}
              <div className="form-actions">
                <button
                  type="button"
                  className="secondary-button"
                  onClick={() => playback.speaking ? stopPlayback() : playback.speak(interaction.speechText)}
                >
                  {playback.speaking ? copy.ttsStopButton : copy.ttsButton}
                </button>
                {playback.notice && <span role="status">{playback.notice}</span>}
                <button type="button" className="text-button" onClick={clearCropQuestion}>
                  {copy.newQuestion}
                </button>
              </div>
            </article>
          )}
        </ReusableCard>
      </section>

      <section className="interaction-workspace" aria-labelledby="farm-analysis-heading">
        <ReusableCard>
          <div className="page-intro">
            <h3 id="farm-analysis-heading">{copy.farmAnalysisTitle}</h3>
            <p>{copy.farmAnalysisDescription}</p>
          </div>
          {farmLoadError ? (
            <ErrorState label={farmLoadError} />
          ) : farms.length === 0 ? (
            <EmptyState title={copy.noRegisteredFarms} description={copy.chooseFarmPlot} />
          ) : (
            <form onSubmit={submitAnalysisForm} className="form-panel">
              <label>
                <span>{copy.selectFarm}</span>
                <select value={farmId} onChange={(event) => selectFarm(event.target.value)} disabled={analysisBusy}>
                  <option value="">{copy.selectFarm}</option>
                  {farms.map((farm) => <option key={farm.farmId} value={farm.farmId}>{farm.name}</option>)}
                </select>
              </label>
              <label>
                <span>{copy.selectPlot}</span>
                <select
                  value={plotId}
                  onChange={(event) => selectPlot(event.target.value)}
                  disabled={analysisBusy || !farmId || plots.length === 0}
                >
                  <option value="">{copy.selectPlot}</option>
                  {plots.map((plot) => (
                    <option key={plot.plotId} value={plot.plotId}>
                      {plot.cropCanonicalName} · {plot.areaM2.value} {plot.areaM2.unit}
                    </option>
                  ))}
                </select>
              </label>
              {farmId && plots.length === 0 && <p role="status">{copy.noPlots}</p>}
              {choicesBusy && <LoadingState label={copy.loading} />}
              {choiceLoadError && <ErrorState label={choiceLoadError} />}
              <label>
                <span>{copy.selectBranch}</span>
                <select
                  value={selectedComparison?.baselineBranchId || branchId}
                  onChange={(event) => { setBranchId(event.target.value); setRunId(""); }}
                  disabled={analysisBusy || !plotId || choicesBusy || Boolean(selectedComparison)}
                >
                  <option value="">{copy.selectBranch}</option>
                  {branches.map((branch) => (
                    <option key={branch.branchId} value={branch.branchId}>
                      {branch.decisionType} · {branch.effectiveDate}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                <span>{copy.selectRun}</span>
                <select
                  value={runId}
                  onChange={(event) => setRunId(event.target.value)}
                  disabled={analysisBusy || !plotId || choicesBusy}
                >
                  <option value="">{copy.selectRun}</option>
                  {availableRuns.map((run) => (
                    <option key={run.simulationRunId} value={run.simulationRunId}>
                      {run.engine || copy.simulationEvidence} · {run.completedAt || run.requestedAt || run.simulationRunId}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                <span>{copy.selectComparison}</span>
                <select
                  value={comparisonId}
                  onChange={(event) => {
                    setComparisonId(event.target.value);
                    setRunId("");
                  }}
                  disabled={analysisBusy || !plotId || choicesBusy}
                >
                  <option value="">{copy.selectComparison}</option>
                  {comparisons.map((comparison) => (
                    <option key={comparison.comparisonId} value={comparison.comparisonId}>
                      {comparison.status} · {comparison.comparisonDate}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                <span>{copy.questionPrompt}</span>
                <textarea
                  value={analysisQuestion}
                  onChange={(event) => setAnalysisQuestion(event.target.value)}
                  placeholder={copy.interactionPlaceholder}
                  rows={3}
                  disabled={analysisBusy}
                />
              </label>
              <div className="form-actions">
                <button type="button" className="secondary-button" onClick={analysisSpeech.toggle}>
                  {analysisSpeech.listening ? copy.stopListening : copy.speakQuestion}
                </button>
                <button
                  type="submit"
                  className="primary-button"
                  disabled={analysisBusy || !farmId || !plotId || !analysisQuestion.trim()}
                >
                  {copy.analyzeButton}
                </button>
                {(analysisQuestion || analysisResult || analysisError) && (
                  <button type="button" className="text-button" onClick={clearAnalysisQuestion}>
                    {copy.newQuestion}
                  </button>
                )}
              </div>
              <p className="warning" role="status">
                {analysisSpeech.notice || (analysisSpeech.supported ? copy.voiceReady : copy.micUnavailable)}
              </p>
              <div className="prompt-list" aria-label={copy.suggestedPrompts}>
                {ANALYSIS_PROMPTS[locale].map((prompt) => (
                  <button
                    key={prompt}
                    type="button"
                    className="secondary-button"
                    onClick={() => setAnalysisQuestion(prompt)}
                    disabled={analysisBusy || !farmId || !plotId}
                  >
                    {prompt}
                  </button>
                ))}
              </div>
            </form>
          )}
          {analysisBusy && <LoadingState label={copy.analysisLoading} />}
          {analysisError && (
            <div>
              <ErrorState label={analysisError} />
              {lastAnalysisRequest && (
                <button type="button" className="secondary-button" onClick={() => void submitFarmAnalysis(lastAnalysisRequest)}>
                  {copy.retry}
                </button>
              )}
            </div>
          )}
          {analysisResult && selectedPlot && (
            <AnalysisAnswer
              result={analysisResult}
              plot={selectedPlot}
              farmName={selectedFarm?.name || ""}
              copy={copy}
              onToggleEvidence={() => setShowEvidence(!showEvidence)}
              showEvidence={showEvidence}
              onSpeak={() => playback.speaking ? stopPlayback() : playback.speak(analysisResult.summary)}
              speaking={playback.speaking}
              playbackNotice={playback.notice}
            />
          )}
        </ReusableCard>
      </section>
    </PageContainer>
  );
}

function AnalysisAnswer({
  result,
  plot,
  farmName,
  copy,
  showEvidence,
  onToggleEvidence,
  onSpeak,
  speaking,
  playbackNotice,
}: {
  result: AnalysisResult;
  plot: Farm["plots"][number];
  farmName: string;
  copy: Translation;
  showEvidence: boolean;
  onToggleEvidence: () => void;
  onSpeak: () => void;
  speaking: boolean;
  playbackNotice: string;
}) {
  const evidence = result.evidenceSummary;
  const mode = result.generationMode === "llm"
    ? copy.llmGenerated
    : result.generationMode === "deterministic_fallback"
      ? copy.fallbackGenerated
      : copy.deterministicGenerated;
  const claims = result.sections.flatMap((section) => section.claims);
  const outputLabels: Record<string, string> = {
    canopyCover: copy.outputCanopyCover,
    biomass: copy.outputBiomass,
    yield: copy.outputYield,
    actualEvapotranspiration: copy.outputEvapotranspiration,
    waterStress: copy.outputWaterStress,
    irrigation: copy.outputIrrigation,
  };
  const freshnessTypeLabels: Record<string, string> = {
    daily_weather_forecast: copy.freshnessWeatherType,
    soil_properties: copy.freshnessSoilType,
    environmental_snapshot: copy.freshnessSnapshotType,
    environmental_input: copy.freshnessInputType,
    scientific_simulation_run: copy.freshnessRunType,
    scientific_simulation_states: copy.freshnessStatesType,
    simulation_comparison: copy.freshnessComparisonType,
  };
  const freshnessStateLabels: Record<string, string> = {
    fresh: copy.freshnessFresh,
    stale: copy.freshnessStale,
    historical: copy.freshnessHistorical,
    static_modelled_baseline: copy.freshnessStaticBaseline,
    missing: copy.freshnessMissing,
    unavailable: copy.freshnessUnavailable,
    new_or_cached: copy.freshnessNewOrCached,
  };
  return (
    <article className="analysis-answer info-card" aria-live="polite">
      <header className="analysis-answer-header">
        <div>
          <p className="eyebrow">{copy.analysisResult}</p>
          <h3>{result.summary}</h3>
          <p>{mode}</p>
        </div>
        <button type="button" className="secondary-button" onClick={onSpeak}>
          {speaking ? copy.ttsStopButton : copy.ttsButton}
        </button>
      </header>
      {playbackNotice && <p className="warning" role="status">{playbackNotice}</p>}
      <ReusableCard>
        <h4>{copy.fieldContext}</h4>
        <p>{farmName} · {plot.cropCanonicalName} · {plot.areaM2.value} {plot.areaM2.unit}</p>
        <p>
          {evidence.cropCanonicalName}
          {evidence.cropScientificName ? ` (${evidence.cropScientificName})` : ""}
          · {evidence.cropEngine} {evidence.cropEngineVersion}
        </p>
      </ReusableCard>
      <ReusableCard>
        <h4>{copy.cropCapability}</h4>
        <p>
          {evidence.cropSupportedOutputs.length
            ? evidence.cropSupportedOutputs.map((output) => outputLabels[output] || output).join(", ")
            : copy.noSupportedOutputs}
        </p>
        {evidence.cropParameterVersions.length > 0 && (
          <p>{evidence.cropParameterVersions.join(", ")}</p>
        )}
        {evidence.cropLimitations.length > 0 && (
          <ul>{evidence.cropLimitations.map((item) => <li key={item}>{item}</li>)}</ul>
        )}
      </ReusableCard>
      <div className="analysis-section-grid">
        {result.sections.map((section) => (
          <ReusableCard key={section.key}>
            <h4>{section.title}</h4>
            <p className="analysis-section-content">{section.content}</p>
            {section.claims.length > 0 && (
              <ul className="grounded-claims">
                {section.claims.map((claim) => (
                  <li key={claim.claimId}>
                    <strong>{claim.metric}: {claim.value} {claim.unit}</strong>
                    <small>{claim.sourceId} · {claim.sourceField}</small>
                    {claim.isStale && <small>{copy.freshnessWarning}</small>}
                    {claim.qualifications.map((qualification) => <small key={qualification}>{qualification}</small>)}
                  </li>
                ))}
              </ul>
            )}
          </ReusableCard>
        ))}
      </div>
      {result.dataFreshness.length > 0 && (
        <ReusableCard>
          <h4>{copy.dataFreshness}</h4>
          {result.dataFreshness.map((freshness) => (
            <p key={`${freshness.sourceId}-${freshness.dataType}`}>
              <strong>
                {freshnessTypeLabels[freshness.dataType] || freshness.dataType}
                {" · "}
                {freshnessStateLabels[freshness.freshnessLabel] || freshness.freshnessLabel}
              </strong>
              {freshness.warning && <span> — {freshness.warning}</span>}
            </p>
          ))}
        </ReusableCard>
      )}
      {(result.scientificLimitations.length > 0 || result.escalations.length > 0) && (
        <ReusableCard>
          <h4>{copy.scientificLimitations}</h4>
          {result.scientificLimitations.map((limitation) => (
            <p key={limitation.code}><strong>{limitation.code}.</strong> {limitation.description} {limitation.implications}</p>
          ))}
          {result.escalations.map((escalation) => (
            <div className="warning" role="alert" key={escalation.category}>
              <strong>{copy.expertFollowUp}: {escalation.recommendedAuthority}</strong>
              <p>{escalation.reason}</p>
              <p>{escalation.recommendedAction}</p>
            </div>
          ))}
        </ReusableCard>
      )}
      <button type="button" className="secondary-button" onClick={onToggleEvidence}>
        {copy.supportingEvidence}
      </button>
      {showEvidence && (
        <div className="analysis-section-grid">
          <ReusableCard>
            <h4>{copy.environmentalEvidence}</h4>
            <p>{evidence.environmentalSource || copy.missingEvidence}</p>
            <p>{copy.sourceField}: {evidence.environmentalSnapshotId || copy.missingEvidence}</p>
            <p>{copy.sourceField}: {evidence.environmentalInputHash || copy.missingEvidence}</p>
            <p>{evidence.weatherDaysCount} {copy.weatherRecords} · {evidence.soilAvailable ? copy.soilProfileAvailable : copy.soilProfileMissing}</p>
          </ReusableCard>
          <ReusableCard>
            <h4>{copy.simulationEvidence}</h4>
            <p>{evidence.simulationStatus || copy.noCompletedRun}</p>
            <p>{copy.sourceField}: {evidence.simulationRunId || copy.missingEvidence}</p>
            <p>{copy.sourceField}: {evidence.branchId || copy.missingEvidence}</p>
            <p>{evidence.simulationEngine} {evidence.simulationEngineVersion} · {evidence.parameterVersion}</p>
            {evidence.simulationCompletedAt && <p>{copy.historicalResult} {evidence.simulationCompletedAt}</p>}
            <p>{copy.sourceField}: {evidence.weatherMemberId || copy.missingEvidence}</p>
            {evidence.simulationWarnings.map((warning) => <p className="warning" key={warning}>{warning}</p>)}
          </ReusableCard>
          {evidence.comparisonId && (
            <ReusableCard>
              <h4>{copy.comparisonEvidence}</h4>
              <p>
                {evidence.comparisonStatus === "comparable"
                  ? copy.comparisonMatched
                  : evidence.comparisonStatus === "not_comparable"
                    ? copy.comparisonNotComparable
                    : copy.comparisonNotMatched}
              </p>
              <p>{copy.sourceField}: {evidence.comparisonId}</p>
              <p>{copy.comparisonBranches}: {evidence.comparisonBaselineBranchId || copy.missingEvidence} · {evidence.comparisonAlternativeBranchId || copy.missingEvidence}</p>
              <p>{copy.comparisonRuns}: {evidence.comparisonBaselineRunId || copy.missingEvidence} · {evidence.comparisonAlternativeRunId || copy.missingEvidence}</p>
              {evidence.comparisonDate && <p>{copy.comparisonDate}: {evidence.comparisonDate}</p>}
              {evidence.comparisonAssumptions.length > 0 && (
                <section>
                  <h4>{copy.comparisonAssumptions}</h4>
                  <ul>{evidence.comparisonAssumptions.map((item) => <li key={item}>{item}</li>)}</ul>
                </section>
              )}
              {evidence.comparisonProvenance.map((source) => (
                <p key={`${source.sourceId}-${source.reference}`}>
                  {source.sourceId} · {source.sourceVersion || ""} · {source.reference || ""}
                </p>
              ))}
              {evidence.comparisonReasons.map((reason) => <p key={reason}>{reason}</p>)}
            </ReusableCard>
          )}
          <ReusableCard>
            <h4>{copy.missingEvidence}</h4>
            <p>{evidence.missingFields.length ? evidence.missingFields.join(", ") : copy.unsupportedNotZero}</p>
          </ReusableCard>
          <ReusableCard>
            <h4>{copy.sourcesTitle}</h4>
            <ul>{claims.map((claim) => (
              <li key={claim.claimId}>{claim.sourceId} · {claim.sourceField}</li>
            ))}</ul>
            {evidence.cropParameterSources.map((source) => (
              <p key={`${source.sourceId}-${source.sourceVersion}`}>
                {source.sourceId} {source.sourceVersion || ""}
              </p>
            ))}
          </ReusableCard>
        </div>
      )}
    </article>
  );
}
