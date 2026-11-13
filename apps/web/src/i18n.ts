export type Locale = "en" | "kn" | "hi";

export const localeLabels: Record<Locale, string> = {
  en: "English",
  kn: "ಕನ್ನಡ",
  hi: "हिन्दी",
};

export type Translation = {
  connect: string;
  assisted: string;
  observatory: string;
  workspace: string;
  cropPlanning: string;
  futureFold: string;
  savedDecisions: string;
  upcoming: string;
  connected: string;
  offline: string;
  language: string;
  welcome: string;
  connectTitle: string;
  connectDescription: string;
  configureTitle: string;
  configureDescription: string;
  configureAction: string;
  capabilitiesTitle: string;
  capabilitiesDescription: string;
  farmWorkspace: string;
  farmWorkspaceDescription: string;
  cropPlanningDescription: string;
  assistedTitle: string;
  assistedDescription: string;
  fieldWorkspace: string;
  fieldWorkspaceDescription: string;
  supportOverview: string;
  supportOverviewDescription: string;
  futureCapability: string;
  observatoryTitle: string;
  observatoryDescription: string;
  viewportLabel: string;
  livingField: string;
  livingFieldDescription: string;
  futureFoldTitle: string;
  futureFoldDescription: string;
  immersiveUnavailable: string;
  immersiveUnavailableDescription: string;
  returnToConnect: string;
  loading: string;
  error: string;
  menu: string;
  notFound: string;
  notFoundDescription: string;
  goToConnect: string;
  version: string;
  interactionTitle: string;
  interactionSubtitle: string;
  interactionPlaceholder: string;
  askButton: string;
  listeningButton: string;
  micUnavailable: string;
  micPermissionDenied: string;
  speechError: string;
  ttsButton: string;
  ttsStopButton: string;
  ttsUnavailable: string;
  suggestedPrompts: string;
  askAnother: string;
  limitationsTitle: string;
  escalationTitle: string;
  sourcesTitle: string;
  cropHelpTitle: string;
  cropHelpDescription: string;
  farmAnalysisTitle: string;
  farmAnalysisDescription: string;
  voiceReady: string;
  textMode: string;
  askUsingText: string;
  speakQuestion: string;
  stopListening: string;
  noSpeech: string;
  recognitionInterrupted: string;
  recognitionLanguageUnsupported: string;
  recognitionNetworkError: string;
  playbackError: string;
  voiceLoading: string;
  newQuestion: string;
  retry: string;
  selectFarm: string;
  selectPlot: string;
  selectBranch: string;
  selectRun: string;
  selectComparison: string;
  questionPrompt: string;
  analyzeButton: string;
  analysisLoading: string;
  analysisResult: string;
  fieldContext: string;
  cropCapability: string;
  environmentalEvidence: string;
  simulationEvidence: string;
  comparisonEvidence: string;
  supportingEvidence: string;
  dataFreshness: string;
  missingEvidence: string;
  scientificLimitations: string;
  expertFollowUp: string;
  generationMode: string;
  sourceField: string;
  freshnessWarning: string;
  noRegisteredFarms: string;
  noPlots: string;
  chooseFarmPlot: string;
  analysisError: string;
  noCompletedRun: string;
  historicalResult: string;
  unsupportedNotZero: string;
  llmGenerated: string;
  deterministicGenerated: string;
  fallbackGenerated: string;
  comparisonMatched: string;
  comparisonNotMatched: string;
  comparisonNotComparable: string;
  comparisonBranches: string;
  comparisonRuns: string;
  comparisonDate: string;
  comparisonAssumptions: string;
  noSupportedOutputs: string;
  outputCanopyCover: string;
  outputBiomass: string;
  outputYield: string;
  outputEvapotranspiration: string;
  outputWaterStress: string;
  outputIrrigation: string;
  freshnessFresh: string;
  freshnessStale: string;
  freshnessHistorical: string;
  freshnessStaticBaseline: string;
  freshnessMissing: string;
  freshnessUnavailable: string;
  freshnessNewOrCached: string;
  freshnessWeatherType: string;
  freshnessSoilType: string;
  freshnessSnapshotType: string;
  freshnessInputType: string;
  freshnessRunType: string;
  freshnessStatesType: string;
  freshnessComparisonType: string;
  weatherRecords: string;
  soilProfileAvailable: string;
  soilProfileMissing: string;
};

export const translations: Record<Locale, Translation> = {
  en: {
    connect: "Connect",
    assisted: "Assisted",
    observatory: "Observatory",
    workspace: "Farm workspace",
    cropPlanning: "Crop planning",
    futureFold: "Future Fold",
    savedDecisions: "Saved decisions",
    upcoming: "Upcoming",
    connected: "Connected",
    offline: "Offline",
    language: "Language",
    welcome: "Welcome to TerraPulse",
    connectTitle: "A clearer view of your farm, season by season.",
    connectDescription:
      "TerraPulse brings your farm context and scientific insight together in one calm workspace.",
    configureTitle: "Your farm workspace is ready when you are.",
    configureDescription:
      "No farm has been configured yet. When onboarding is available, this is where your farm context will live.",
    configureAction: "Explore TerraPulse",
    capabilitiesTitle: "Built for better decisions",
    capabilitiesDescription: "A foundation for the tools that will support your next growing season.",
    farmWorkspace: "Farm workspace",
    farmWorkspaceDescription: "Bring your fields, context and priorities into one place.",
    cropPlanningDescription: "Plan with confidence using clear, locally relevant guidance.",
    assistedTitle: "Support every field conversation",
    assistedDescription:
      "A dedicated workspace for FPOs and field workers to guide farmers with shared context.",
    fieldWorkspace: "Field-worker workspace",
    fieldWorkspaceDescription: "A focused place for the people who help farming communities thrive.",
    supportOverview: "Farmer-support overview",
    supportOverviewDescription: "Member assistance tools will appear here as they become available.",
    futureCapability: "Future capability",
    observatoryTitle: "See the living system",
    observatoryDescription:
      "The Observatory will become TerraPulse’s scientific exploration space: a window into the living field.",
    viewportLabel: "Living Field visualization viewport",
    livingField: "3D Living Field",
    livingFieldDescription:
      "An immersive view of your agricultural system is being prepared for a future release.",
    futureFoldTitle: "Future Fold",
    futureFoldDescription:
      "Trace the conditions, signals and decisions that shape what comes next.",
    immersiveUnavailable: "Immersive rendering is unavailable",
    immersiveUnavailableDescription:
      "This browser or device does not support the WebGL rendering needed for the Living Field. You can still use the rest of TerraPulse.",
    returnToConnect: "Return to Connect",
    loading: "Loading",
    error: "Something went wrong",
    menu: "Open navigation",
    notFound: "Page not found",
    notFoundDescription: "That TerraPulse workspace does not exist yet.",
    goToConnect: "Go to Connect",
    version: "TerraPulse 2.0 · Browser workspace",
    interactionTitle: "Farmer Voice & Text Advisory",
    interactionSubtitle: "Ask bounded crop, water, and capability questions in English, Kannada, or Hindi with speech support.",
    interactionPlaceholder: "Ask about crop identity, water needs, or capability (e.g., 'I grow turmeric')...",
    askButton: "Ask Question",
    listeningButton: "Listening… Speak now",
    micUnavailable: "Speech recognition is not supported in this browser. Please use text/touch input.",
    micPermissionDenied: "Microphone permission was denied. Please use text/touch input.",
    speechError: "Speech recognition error. Please retry or type your question.",
    ttsButton: "Listen to Answer",
    ttsStopButton: "Stop Audio",
    ttsUnavailable: "Speech voice for this language is not installed on this browser/OS (requires an OS language voice pack). The complete text response is available above.",
    suggestedPrompts: "Suggested Questions",
    askAnother: "Ask Another Question",
    limitationsTitle: "Scientific Limitations & Biophysical Scope",
    escalationTitle: "Expert Referral Required (ICAR / KVK)",
    sourcesTitle: "Sources & Provenance",
    cropHelpTitle: "Crop & Capability Help",
    cropHelpDescription: "Bounded crop identity, model capability and general water guidance. This is not a diagnostic chatbot.",
    farmAnalysisTitle: "Analyze My Farm",
    farmAnalysisDescription: "Ask about a registered field using its stored environmental and scientific evidence.",
    voiceReady: "Voice input available",
    textMode: "Text and touch are always available",
    askUsingText: "Ask using text",
    speakQuestion: "Speak your question",
    stopListening: "Stop listening",
    noSpeech: "No speech was detected. You can edit or type your question.",
    recognitionInterrupted: "Speech input stopped before a transcript was received. Please try again or type.",
    recognitionLanguageUnsupported: "Speech recognition does not support this language on this device. Please type your question.",
    recognitionNetworkError: "The speech service could not be reached. Please type your question.",
    playbackError: "Audio playback failed or was interrupted. The text response is still available.",
    voiceLoading: "Checking available device voices. Please try again in a moment.",
    newQuestion: "New question",
    retry: "Retry",
    selectFarm: "Select your farm",
    selectPlot: "Select your field/plot",
    selectBranch: "Branch (optional)",
    selectRun: "Completed simulation run (optional)",
    selectComparison: "Saved comparison (optional)",
    questionPrompt: "What would you like to understand?",
    analyzeButton: "Analyze my farm",
    analysisLoading: "Retrieving and checking your farm evidence…",
    analysisResult: "Evidence-based answer",
    fieldContext: "Field context",
    cropCapability: "Crop capability",
    environmentalEvidence: "Environmental evidence",
    simulationEvidence: "Scientific simulation",
    comparisonEvidence: "Comparison evidence",
    supportingEvidence: "View supporting evidence",
    dataFreshness: "Data freshness",
    missingEvidence: "Information not available",
    scientificLimitations: "Why this result is limited",
    expertFollowUp: "Suggested human follow-up",
    generationMode: "How this answer was prepared",
    sourceField: "Evidence field",
    freshnessWarning: "Historical or stale data",
    noRegisteredFarms: "No registered farms are available. Add a real farm before requesting farm analysis.",
    noPlots: "No registered plots are available for this farm.",
    chooseFarmPlot: "Choose a farm and plot before asking for an analysis.",
    analysisError: "Analysis could not be completed. Check your connection and try again.",
    noCompletedRun: "No completed simulation is available for this selection.",
    historicalResult: "Historical simulation result; not a live forecast.",
    unsupportedNotZero: "Unsupported or missing measurements are not zero.",
    llmGenerated: "Optional AI-assisted explanation with validated evidence",
    deterministicGenerated: "Deterministic evidence explanation",
    fallbackGenerated: "Deterministic fallback after AI output was unavailable or rejected",
    comparisonMatched: "Comparable inputs",
    comparisonNotMatched: "Inputs did not match",
    comparisonNotComparable: "Not comparable",
    comparisonBranches: "Baseline and alternative branches",
    comparisonRuns: "Baseline and alternative simulation runs",
    comparisonDate: "Comparison date",
    comparisonAssumptions: "Comparison assumptions",
    noSupportedOutputs: "This crop has no supported numeric outputs in the current model.",
    outputCanopyCover: "Canopy cover",
    outputBiomass: "Biomass",
    outputYield: "Yield",
    outputEvapotranspiration: "Actual evapotranspiration",
    outputWaterStress: "Water stress",
    outputIrrigation: "Irrigation",
    freshnessFresh: "Fresh",
    freshnessStale: "Stale",
    freshnessHistorical: "Historical",
    freshnessStaticBaseline: "Static modelled baseline",
    freshnessMissing: "Missing",
    freshnessUnavailable: "Unavailable",
    freshnessNewOrCached: "New or cached",
    freshnessWeatherType: "Weather evidence",
    freshnessSoilType: "Soil evidence",
    freshnessSnapshotType: "Environmental snapshot",
    freshnessInputType: "Environmental input",
    freshnessRunType: "Scientific simulation run",
    freshnessStatesType: "Scientific simulation states",
    freshnessComparisonType: "Simulation comparison",
    weatherRecords: "weather records",
    soilProfileAvailable: "Soil profile available",
    soilProfileMissing: "Soil profile unavailable",
  },
  kn: {
    connect: "ಕನೆಕ್ಟ್",
    assisted: "ಸಹಾಯಿತ",
    observatory: "ವೀಕ್ಷಣಾಲಯ",
    workspace: "ಕೃಷಿ ಕಾರ್ಯಕ್ಷೇತ್ರ",
    cropPlanning: "ಬೆಳೆ ಯೋಜನೆ",
    futureFold: "ಭವಿಷ್ಯದ ಹಂತ",
    savedDecisions: "ಉಳಿಸಿದ ನಿರ್ಧಾರಗಳು",
    upcoming: "ಶೀಘ್ರದಲ್ಲೇ",
    connected: "ಸಂಪರ್ಕಿಸಲಾಗಿದೆ",
    offline: "ಆಫ್‌ಲೈನ್",
    language: "ಭಾಷೆ",
    welcome: "TerraPulse ಗೆ ಸ್ವಾಗತ",
    connectTitle: "ಪ್ರತಿ ಋತುವಿನಲ್ಲಿ ನಿಮ್ಮ ಕೃಷಿಯ ಸ್ಪಷ್ಟ ಚಿತ್ರಣ.",
    connectDescription: "TerraPulse ನಿಮ್ಮ ಕೃಷಿ ಸಂದರ್ಭ ಮತ್ತು ವೈಜ್ಞಾನಿಕ ಒಳನೋಟವನ್ನು ಒಂದೇ ಕಾರ್ಯಕ್ಷೇತ್ರದಲ್ಲಿ ತರುತ್ತದೆ.",
    configureTitle: "ನಿಮ್ಮ ಕೃಷಿ ಕಾರ್ಯಕ್ಷೇತ್ರ ಸಿದ್ಧವಾಗಿದೆ.",
    configureDescription: "ಇನ್ನೂ ಯಾವುದೇ ಕೃಷಿಯನ್ನು ಹೊಂದಿಸಲಾಗಿಲ್ಲ. ಆನ್‌ಬೋರ್ಡಿಂಗ್ ಲಭ್ಯವಾದಾಗ ನಿಮ್ಮ ಕೃಷಿ ಸಂದರ್ಭ ಇಲ್ಲಿ ಕಾಣಿಸುತ್ತದೆ.",
    configureAction: "TerraPulse ಅನ್ವೇಷಿಸಿ",
    capabilitiesTitle: "ಉತ್ತಮ ನಿರ್ಧಾರಗಳಿಗಾಗಿ ನಿರ್ಮಿಸಲಾಗಿದೆ",
    capabilitiesDescription: "ಮುಂದಿನ ಬೆಳೆಯ ಋತುವಿಗೆ ಸಹಾಯ ಮಾಡುವ ಸಾಧನಗಳಿಗೆ ಒಂದು ಅಡಿಪಾಯ.",
    farmWorkspace: "ಕೃಷಿ ಕಾರ್ಯಕ್ಷೇತ್ರ",
    farmWorkspaceDescription: "ನಿಮ್ಮ ಹೊಲಗಳು, ಸಂದರ್ಭ ಮತ್ತು ಆದ್ಯತೆಗಳನ್ನು ಒಂದೇ ಸ್ಥಳಕ್ಕೆ ತಂದುಕೊಳ್ಳಿ.",
    cropPlanningDescription: "ಸ್ಪಷ್ಟ ಮತ್ತು ಸ್ಥಳೀಯ ಮಾರ್ಗದರ್ಶನದೊಂದಿಗೆ ಯೋಜಿಸಿ.",
    assistedTitle: "ಪ್ರತಿ ಕೃಷಿ ಸಂಭಾಷಣೆಗೆ ಬೆಂಬಲ",
    assistedDescription: "FPOಗಳು ಮತ್ತು ಕ್ಷೇತ್ರ ಕಾರ್ಯಕರ್ತರು ರೈತರಿಗೆ ಸಹಾಯ ಮಾಡಲು ಮೀಸಲಾದ ಕಾರ್ಯಕ್ಷೇತ್ರ.",
    fieldWorkspace: "ಕ್ಷೇತ್ರ ಕಾರ್ಯಕರ್ತರ ಕಾರ್ಯಕ್ಷೇತ್ರ",
    fieldWorkspaceDescription: "ಕೃಷಿ ಸಮುದಾಯಗಳನ್ನು ಬೆಳೆಸುವವರಿಗೆ ಒಂದು ಕೇಂದ್ರೀಕೃತ ಸ್ಥಳ.",
    supportOverview: "ರೈತರ ಬೆಂಬಲದ ಅವಲೋಕನ",
    supportOverviewDescription: "ಸದಸ್ಯ ಸಹಾಯ ಸಾಧನಗಳು ಲಭ್ಯವಾದಂತೆ ಇಲ್ಲಿ ಕಾಣಿಸುತ್ತವೆ.",
    futureCapability: "ಭವಿಷ್ಯದ ಸಾಮರ್ಥ್ಯ",
    observatoryTitle: "ಜೀವಂತ ವ್ಯವಸ್ಥೆಯನ್ನು ನೋಡಿ",
    observatoryDescription: "ವೀಕ್ಷಣಾಲಯವು TerraPulse ನ ವೈಜ್ಞಾನಿಕ ಅನ್ವೇಷಣೆಯ ಸ್ಥಳವಾಗಲಿದೆ.",
    viewportLabel: "ಲಿವಿಂಗ್ ಫೀಲ್ಡ್ ದೃಶ್ಯೀಕರಣ ಪ್ರದೇಶ",
    livingField: "3D ಲಿವಿಂಗ್ ಫೀಲ್ಡ್",
    livingFieldDescription: "ನಿಮ್ಮ ಕೃಷಿ ವ್ಯವಸ್ಥೆಯ ಆಳವಾದ ನೋಟವನ್ನು ಮುಂದಿನ ಬಿಡುಗಡೆಗಾಗಿ ಸಿದ್ಧಪಡಿಸಲಾಗುತ್ತಿದೆ.",
    futureFoldTitle: "ಭವಿಷ್ಯದ ಹಂತ",
    futureFoldDescription: "ಮುಂದಿನ ಹಂತವನ್ನು ರೂಪಿಸುವ ಪರಿಸ್ಥಿತಿಗಳು ಮತ್ತು ನಿರ್ಧಾರಗಳನ್ನು ಅನುಸರಿಸಿ.",
    immersiveUnavailable: "ತಲ್ಲೀನಗೊಳಿಸುವ ರೆಂಡರಿಂಗ್ ಲಭ್ಯವಿಲ್ಲ",
    immersiveUnavailableDescription: "ಈ ಬ್ರೌಸರ್ WebGL ಅನ್ನು ಬೆಂಬಲಿಸುವುದಿಲ್ಲ. TerraPulse ನ ಉಳಿದ ಭಾಗವನ್ನು ಬಳಸಬಹುದು.",
    returnToConnect: "ಕನೆಕ್ಟ್‌ಗೆ ಹಿಂತಿರುಗಿ",
    loading: "ಲೋಡ್ ಆಗುತ್ತಿದೆ",
    error: "ಏನೋ ತಪ್ಪಾಗಿದೆ",
    menu: "ನ್ಯಾವಿಗೇಶನ್ ತೆರೆಯಿರಿ",
    notFound: "ಪುಟ ಕಂಡುಬಂದಿಲ್ಲ",
    notFoundDescription: "ಈ TerraPulse ಕಾರ್ಯಕ್ಷೇತ್ರ ಇನ್ನೂ ಅಸ್ತಿತ್ವದಲ್ಲಿಲ್ಲ.",
    goToConnect: "ಕನೆಕ್ಟ್‌ಗೆ ಹೋಗಿ",
    version: "TerraPulse 2.0 · ಬ್ರೌಸರ್ ಕಾರ್ಯಕ್ಷೇತ್ರ",
    interactionTitle: "ರೈತರ ಧ್ವನಿ ಮತ್ತು ಪಠ್ಯ ಸಮಾಲೋಚನೆ",
    interactionSubtitle: "ಕನ್ನಡ, ಇಂಗ್ಲಿಷ್ ಅಥವಾ ಹಿಂದಿಯಲ್ಲಿ ಬೆಳೆ ಮತ್ತು ನೀರಿನ ನಿರ್ಧಾರಗಳ ಕುರಿತು ಧ್ವನಿ ಅಥವಾ ಪಠ್ಯದ ಮೂಲಕ ಪ್ರಶ್ನಿಸಿ.",
    interactionPlaceholder: "ನಿಮ್ಮ ಬೆಳೆ ಅಥವಾ ನೀರಿನ ಅಗತ್ಯತೆಯ ಬಗ್ಗೆ ಕೇಳಿ (ಉದಾ: 'ನನ್ನ ಬೆಳೆ ಅರಿಶಿನ')...",
    askButton: "ಪ್ರಶ್ನಿಸಿ",
    listeningButton: "ಆಲಿಸಲಾಗುತ್ತಿದೆ… ಮಾತನಾಡಿ",
    micUnavailable: "ಈ ಬ್ರೌಸರ್‌ನಲ್ಲಿ ಧ್ವನಿ ಗುರುತಿಸುವಿಕೆ ಬೆಂಬಲಿತವಾಗಿಲ್ಲ. ದಯವಿಟ್ಟು ಪಠ್ಯವನ್ನು ಬಳಸಿ.",
    micPermissionDenied: "ಮೈಕ್ರೋಫೋನ್ ಅನುಮತಿ ನಿರಾಕರಿಸಲಾಗಿದೆ. ದಯವಿಟ್ಟು ಪಠ್ಯವನ್ನು ಬಳಸಿ.",
    speechError: "ಧ್ವನಿ ಗುರುತಿಸುವಿಕೆಯಲ್ಲಿ ದೋಷ ಸಂಭವಿಸಿದೆ. ದಯವಿಟ್ಟು ಪಠ್ಯವನ್ನು ಬಳಸಿ.",
    ttsButton: "ಉತ್ತರವನ್ನು ಆಲಿಸಿ",
    ttsStopButton: "ಧ್ವನಿ ನಿಲ್ಲಿಸಿ",
    ttsUnavailable: "ಈ ಭಾಷೆಯ ಧ್ವನಿ ಪ್ಯಾಕ್ ಈ ಬ್ರೌಸರ್/OS ನಲ್ಲಿ ಲಭ್ಯವಿಲ್ಲ (OS ಭಾಷಾ ಧ್ವನಿ ಪ್ಯಾಕ್ ಅಗತ್ಯವಿದೆ). ಮೇಲಿನ ಪೂರ್ಣ ಪಠ್ಯ ಪ್ರತಿಕ್ರಿಯೆಯನ್ನು ಓದಬಹುದು.",
    suggestedPrompts: "ಸೂಚಿಸಲಾದ ಪ್ರಶ್ನೆಗಳು",
    askAnother: "ಮತ್ತೊಂದು ಪ್ರಶ್ನೆ ಕೇಳಿ",
    limitationsTitle: "ವೈಜ್ಞಾನಿಕ ಮಿತಿಗಳು ಮತ್ತು ಊಹೆಗಳು",
    escalationTitle: "ತಜ್ಞರ ಸಲಹೆ ಅಗತ್ಯವಿದೆ (ಕೃಷಿ ವಿಜ್ಞಾನ ಕೇಂದ್ರ)",
    sourcesTitle: "ಮೂಲಗಳು ಮತ್ತು ಉಲ್ಲೇಖಗಳು",
    cropHelpTitle: "ಬೆಳೆ ಮತ್ತು ಸಾಮರ್ಥ್ಯ ಸಹಾಯ",
    cropHelpDescription: "ಬೆಳೆ ಗುರುತು, ಮಾದರಿ ಸಾಮರ್ಥ್ಯ ಮತ್ತು ಸಾಮಾನ್ಯ ನೀರಿನ ಮಾರ್ಗದರ್ಶನ ಮಾತ್ರ. ಇದು ರೋಗನಿರ್ಣಯ ಚಾಟ್‌ಬಾಟ್ ಅಲ್ಲ.",
    farmAnalysisTitle: "ನನ್ನ ಕೃಷಿಯನ್ನು ವಿಶ್ಲೇಷಿಸಿ",
    farmAnalysisDescription: "ನೋಂದಾಯಿತ ಹೊಲದ ಸಂಗ್ರಹಿತ ಪರಿಸರ ಮತ್ತು ವೈಜ್ಞಾನಿಕ ಸಾಕ್ಷ್ಯಗಳ ಬಗ್ಗೆ ಕೇಳಿ.",
    voiceReady: "ಧ್ವನಿ ಇನ್‌ಪುಟ್ ಲಭ್ಯವಿದೆ",
    textMode: "ಪಠ್ಯ ಮತ್ತು ಸ್ಪರ್ಶ ಇನ್‌ಪುಟ್ ಯಾವಾಗಲೂ ಲಭ್ಯ",
    askUsingText: "ಪಠ್ಯದಲ್ಲಿ ಪ್ರಶ್ನಿಸಿ",
    speakQuestion: "ನಿಮ್ಮ ಪ್ರಶ್ನೆಯನ್ನು ಮಾತನಾಡಿ",
    stopListening: "ಆಲಿಸುವುದನ್ನು ನಿಲ್ಲಿಸಿ",
    noSpeech: "ಧ್ವನಿ ಪತ್ತೆಯಾಗಲಿಲ್ಲ. ಪ್ರಶ್ನೆಯನ್ನು ತಿದ್ದಿ ಅಥವಾ ಟೈಪ್ ಮಾಡಿ.",
    recognitionInterrupted: "ಪ್ರತಿಲಿಪಿ ಸಿಗುವ ಮೊದಲು ಧ್ವನಿ ಇನ್‌ಪುಟ್ ನಿಂತಿತು. ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ ಅಥವಾ ಟೈಪ್ ಮಾಡಿ.",
    recognitionLanguageUnsupported: "ಈ ಸಾಧನದಲ್ಲಿ ಈ ಭಾಷೆಯ ಧ್ವನಿ ಗುರುತಿಸುವಿಕೆ ಬೆಂಬಲಿತವಿಲ್ಲ. ಪ್ರಶ್ನೆಯನ್ನು ಟೈಪ್ ಮಾಡಿ.",
    recognitionNetworkError: "ಧ್ವನಿ ಸೇವೆಯನ್ನು ಸಂಪರ್ಕಿಸಲಾಗಲಿಲ್ಲ. ಪ್ರಶ್ನೆಯನ್ನು ಟೈಪ್ ಮಾಡಿ.",
    playbackError: "ಧ್ವನಿ ಪ್ಲೇಬ್ಯಾಕ್ ವಿಫಲವಾಗಿದೆ ಅಥವಾ ನಿಂತಿದೆ. ಪಠ್ಯ ಉತ್ತರ ಲಭ್ಯವಿದೆ.",
    voiceLoading: "ಸಾಧನದ ಧ್ವನಿಗಳನ್ನು ಪರಿಶೀಲಿಸಲಾಗುತ್ತಿದೆ. ಸ್ವಲ್ಪ ಸಮಯದ ಬಳಿಕ ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ.",
    newQuestion: "ಹೊಸ ಪ್ರಶ್ನೆ",
    retry: "ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ",
    selectFarm: "ನಿಮ್ಮ ಕೃಷಿಯನ್ನು ಆಯ್ಕೆಮಾಡಿ",
    selectPlot: "ನಿಮ್ಮ ಹೊಲ/ಪ್ಲಾಟ್ ಆಯ್ಕೆಮಾಡಿ",
    selectBranch: "ಶಾಖೆ (ಐಚ್ಛಿಕ)",
    selectRun: "ಪೂರ್ಣಗೊಂಡ ಸಿಮ್ಯುಲೇಶನ್ (ಐಚ್ಛಿಕ)",
    selectComparison: "ಉಳಿಸಿದ ಹೋಲಿಕೆ (ಐಚ್ಛಿಕ)",
    questionPrompt: "ನೀವು ಏನನ್ನು ಅರ್ಥಮಾಡಿಕೊಳ್ಳಲು ಬಯಸುತ್ತೀರಿ?",
    analyzeButton: "ನನ್ನ ಕೃಷಿಯನ್ನು ವಿಶ್ಲೇಷಿಸಿ",
    analysisLoading: "ನಿಮ್ಮ ಕೃಷಿಯ ಸಾಕ್ಷ್ಯವನ್ನು ಪಡೆಯಲಾಗುತ್ತಿದೆ ಮತ್ತು ಪರಿಶೀಲಿಸಲಾಗುತ್ತಿದೆ…",
    analysisResult: "ಸಾಕ್ಷ್ಯಾಧಾರಿತ ಉತ್ತರ",
    fieldContext: "ಹೊಲದ ಸಂದರ್ಭ",
    cropCapability: "ಬೆಳೆ ಮಾದರಿ ಸಾಮರ್ಥ್ಯ",
    environmentalEvidence: "ಪರಿಸರ ಸಾಕ್ಷ್ಯ",
    simulationEvidence: "ವೈಜ್ಞಾನಿಕ ಸಿಮ್ಯುಲೇಶನ್",
    comparisonEvidence: "ಹೋಲಿಕೆಯ ಸಾಕ್ಷ್ಯ",
    supportingEvidence: "ಬೆಂಬಲಿಸುವ ಸಾಕ್ಷ್ಯವನ್ನು ನೋಡಿ",
    dataFreshness: "ದತ್ತಾಂಶದ ತಾಜಾತನ",
    missingEvidence: "ಮಾಹಿತಿ ಲಭ್ಯವಿಲ್ಲ",
    scientificLimitations: "ಈ ಫಲಿತಾಂಶದ ಮಿತಿಗಳು",
    expertFollowUp: "ಮಾನವ ತಜ್ಞರ ಮುಂದಿನ ಸಲಹೆ",
    generationMode: "ಈ ಉತ್ತರವನ್ನು ಹೇಗೆ ಸಿದ್ಧಪಡಿಸಲಾಗಿದೆ",
    sourceField: "ಸಾಕ್ಷ್ಯ ಕ್ಷೇತ್ರ",
    freshnessWarning: "ಹಳೆಯ ಅಥವಾ ಅವಧಿ ಮೀರಿದ ದತ್ತಾಂಶ",
    noRegisteredFarms: "ನೋಂದಾಯಿತ ಕೃಷಿ ಲಭ್ಯವಿಲ್ಲ. ವಿಶ್ಲೇಷಣೆಗೆ ಮೊದಲು ನೈಜ ಕೃಷಿಯನ್ನು ಸೇರಿಸಿ.",
    noPlots: "ಈ ಕೃಷಿಗೆ ನೋಂದಾಯಿತ ಹೊಲಗಳಿಲ್ಲ.",
    chooseFarmPlot: "ವಿಶ್ಲೇಷಣೆ ಕೇಳುವ ಮೊದಲು ಕೃಷಿ ಮತ್ತು ಹೊಲವನ್ನು ಆಯ್ಕೆಮಾಡಿ.",
    analysisError: "ವಿಶ್ಲೇಷಣೆ ಪೂರ್ಣಗೊಳ್ಳಲಿಲ್ಲ. ಸಂಪರ್ಕ ಪರಿಶೀಲಿಸಿ ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ.",
    noCompletedRun: "ಈ ಆಯ್ಕೆಗೆ ಪೂರ್ಣಗೊಂಡ ಸಿಮ್ಯುಲೇಶನ್ ಲಭ್ಯವಿಲ್ಲ.",
    historicalResult: "ಹಿಂದಿನ ಸಿಮ್ಯುಲೇಶನ್ ಫಲಿತಾಂಶ; ಇದು ಪ್ರಸ್ತುತ ಮುನ್ಸೂಚನೆ ಅಲ್ಲ.",
    unsupportedNotZero: "ಬೆಂಬಲಿಸದ ಅಥವಾ ಕಾಣೆಯಾದ ಅಳತೆಗಳು ಶೂನ್ಯವಲ್ಲ.",
    llmGenerated: "ಪರಿಶೀಲಿಸಿದ ಸಾಕ್ಷ್ಯವಿರುವ ಐಚ್ಛಿಕ AI ವಿವರಣೆ",
    deterministicGenerated: "ನಿಯಮಾಧಾರಿತ ಸಾಕ್ಷ್ಯ ವಿವರಣೆ",
    fallbackGenerated: "AI ಉತ್ತರ ಲಭ್ಯವಿಲ್ಲದಾಗ ಅಥವಾ ತಿರಸ್ಕೃತವಾದಾಗ ನಿಯಮಾಧಾರಿತ ಉತ್ತರ",
    comparisonMatched: "ಹೋಲಿಸಬಹುದಾದ ಇನ್‌ಪುಟ್‌ಗಳು",
    comparisonNotMatched: "ಇನ್‌ಪುಟ್‌ಗಳು ಹೊಂದಿಕೆಯಾಗಿಲ್ಲ",
    comparisonNotComparable: "ಹೋಲಿಸಲಾಗದು",
    comparisonBranches: "ಮೂಲ ಮತ್ತು ಪರ್ಯಾಯ ಶಾಖೆಗಳು",
    comparisonRuns: "ಮೂಲ ಮತ್ತು ಪರ್ಯಾಯ ಸಿಮ್ಯುಲೇಶನ್ ರನ್‌ಗಳು",
    comparisonDate: "ಹೋಲಿಕೆಯ ದಿನಾಂಕ",
    comparisonAssumptions: "ಹೋಲಿಕೆಯ ಊಹೆಗಳು",
    noSupportedOutputs: "ಈ ಬೆಳೆಗೆ ಪ್ರಸ್ತುತ ಮಾದರಿಯಲ್ಲಿ ಬೆಂಬಲಿತ ಸಂಖ್ಯಾತ್ಮಕ ಫಲಿತಾಂಶಗಳಿಲ್ಲ.",
    outputCanopyCover: "ಬೆಳೆ ಮೇಲ್ಛಾವಣಿ ವ್ಯಾಪ್ತಿ",
    outputBiomass: "ಜೈವಭಾರ",
    outputYield: "ಇಳುವರಿ",
    outputEvapotranspiration: "ನೈಜ ಬಾಷ್ಪೀಕರಣ",
    outputWaterStress: "ನೀರಿನ ಒತ್ತಡ",
    outputIrrigation: "ನೀರಾವರಿ",
    freshnessFresh: "ತಾಜಾ",
    freshnessStale: "ಹಳೆಯದು",
    freshnessHistorical: "ಹಿಂದಿನದು",
    freshnessStaticBaseline: "ಸ್ಥಿರ ಮಾದರಿ ಆಧಾರ",
    freshnessMissing: "ಕಾಣೆಯಾಗಿದೆ",
    freshnessUnavailable: "ಲಭ್ಯವಿಲ್ಲ",
    freshnessNewOrCached: "ಹೊಸದು ಅಥವಾ ಸಂಗ್ರಹಿತ",
    freshnessWeatherType: "ಹವಾಮಾನ ಸಾಕ್ಷ್ಯ",
    freshnessSoilType: "ಮಣ್ಣಿನ ಸಾಕ್ಷ್ಯ",
    freshnessSnapshotType: "ಪರಿಸರ ಸ್ನ್ಯಾಪ್‌ಶಾಟ್",
    freshnessInputType: "ಪರಿಸರ ಇನ್‌ಪುಟ್",
    freshnessRunType: "ವೈಜ್ಞಾನಿಕ ಸಿಮ್ಯುಲೇಶನ್ ರನ್",
    freshnessStatesType: "ವೈಜ್ಞಾನಿಕ ಸಿಮ್ಯುಲೇಶನ್ ಸ್ಥಿತಿಗಳು",
    freshnessComparisonType: "ಸಿಮ್ಯುಲೇಶನ್ ಹೋಲಿಕೆ",
    weatherRecords: "ಹವಾಮಾನ ದಾಖಲೆಗಳು",
    soilProfileAvailable: "ಮಣ್ಣಿನ ವಿವರ ಲಭ್ಯವಿದೆ",
    soilProfileMissing: "ಮಣ್ಣಿನ ವಿವರ ಲಭ್ಯವಿಲ್ಲ",
  },
  hi: {
    connect: "कनेक्ट",
    assisted: "सहायित",
    observatory: "वेधशाला",
    workspace: "फार्म कार्यक्षेत्र",
    cropPlanning: "फसल योजना",
    futureFold: "भविष्य की परत",
    savedDecisions: "सहेजे निर्णय",
    upcoming: "जल्द आ रहा है",
    connected: "कनेक्टेड",
    offline: "ऑफलाइन",
    language: "भाषा",
    welcome: "TerraPulse में आपका स्वागत है",
    connectTitle: "हर मौसम में अपने फार्म को बेहतर समझें।",
    connectDescription: "TerraPulse आपके फार्म के संदर्भ और वैज्ञानिक जानकारी को एक शांत कार्यक्षेत्र में लाता है।",
    configureTitle: "आपका फार्म कार्यक्षेत्र तैयार है।",
    configureDescription: "अभी कोई फार्म कॉन्फ़िगर नहीं किया गया है। ऑनबोर्डिंग उपलब्ध होने पर आपका संदर्भ यहां दिखेगा।",
    configureAction: "TerraPulse देखें",
    capabilitiesTitle: "बेहतर निर्णयों के लिए बनाया गया",
    capabilitiesDescription: "अगले फसल मौसम में मदद करने वाले औजारों की नींव।",
    farmWorkspace: "फार्म कार्यक्षेत्र",
    farmWorkspaceDescription: "अपने खेत, संदर्भ और प्राथमिकताओं को एक ही जगह पर लाएं।",
    cropPlanningDescription: "स्पष्ट और स्थानीय मार्गदर्शन के साथ योजना बनाएं।",
    assistedTitle: "हर खेत की बातचीत में सहयोग",
    assistedDescription: "FPO और फील्ड वर्कर के लिए किसानों का मार्गदर्शन करने वाला कार्यक्षेत्र।",
    fieldWorkspace: "फील्ड वर्कर कार्यक्षेत्र",
    fieldWorkspaceDescription: "कृषि समुदायों की मदद करने वालों के लिए एक केंद्रित जगह।",
    supportOverview: "किसान सहायता अवलोकन",
    supportOverviewDescription: "सदस्य सहायता के औजार उपलब्ध होने पर यहां दिखाई देंगे।",
    futureCapability: "भविष्य की सुविधा",
    observatoryTitle: "जीवंत प्रणाली को समझें",
    observatoryDescription: "वेधशाला TerraPulse का वैज्ञानिक अन्वेषण स्थान बनेगी।",
    viewportLabel: "लिविंग फील्ड विज़ुअलाइज़ेशन क्षेत्र",
    livingField: "3D लिविंग फील्ड",
    livingFieldDescription: "आपकी कृषि प्रणाली का विस्तृत दृश्य भविष्य के संस्करण के लिए तैयार किया जा रहा है।",
    futureFoldTitle: "भविष्य की परत",
    futureFoldDescription: "आगे के निर्णयों को आकार देने वाली परिस्थितियों और संकेतों को समझें।",
    immersiveUnavailable: "इमर्सिव रेंडरिंग उपलब्ध नहीं है",
    immersiveUnavailableDescription: "यह ब्राउज़र WebGL रेंडरिंग का समर्थन नहीं करता। आप TerraPulse के बाकी हिस्से का उपयोग कर सकते हैं।",
    returnToConnect: "कनेक्ट पर लौटें",
    loading: "लोड हो रहा है",
    error: "कुछ गलत हो गया",
    menu: "नेविगेशन खोलें",
    notFound: "पृष्ठ नहीं मिला",
    notFoundDescription: "यह TerraPulse कार्यक्षेत्र अभी मौजूद नहीं है।",
    goToConnect: "कनेक्ट पर जाएं",
    version: "TerraPulse 2.0 · ब्राउज़र कार्यक्षेत्र",
    interactionTitle: "किसान आवाज एवं पाठ्य परामर्श",
    interactionSubtitle: "फसल पहचान, जल संतुलन और उपज क्षमताओं के बारे में हिंदी, कन्नड़ या अंग्रेजी में पूछें।",
    interactionPlaceholder: "अपनी फसल या पानी की आवश्यकता के बारे में पूछें (जैसे: 'मेरी फसल हल्दी है')...",
    askButton: "पूछें",
    listeningButton: "सुन रहे हैं… बोलिए",
    micUnavailable: "इस ब्राउज़र में आवाज पहचान समर्थित नहीं है। कृपया लिखकर प्रश्न पूछें।",
    micPermissionDenied: "माइक्रोफ़ोन की अनुमति अस्वीकृत की गई। कृपया लिखकर प्रश्न पूछें।",
    speechError: "आवाज पहचान में त्रुटि हुई। कृपया पुनः प्रयास करें या लिखकर पूछें।",
    ttsButton: "उत्तर सुनें",
    ttsStopButton: "आवाज रोकें",
    ttsUnavailable: "इस भाषा का वॉइस पैक इस ब्राउज़र/OS पर उपलब्ध नहीं है (OS वॉइस पैक आवश्यक है)। ऊपर दिया गया पूर्ण उत्तर पढ़ें।",
    suggestedPrompts: "सुझाए गए प्रश्न",
    askAnother: "दूसरा प्रश्न पूछें",
    limitationsTitle: "वैज्ञानिक सीमाएं एवं बायोफिजिकल दायरा",
    escalationTitle: "विशेषज्ञ परामर्श आवश्यक (कृषि विज्ञान केंद्र)",
    sourcesTitle: "प्रमाणिक स्रोत एवं संदर्भ",
    cropHelpTitle: "फसल और क्षमता सहायता",
    cropHelpDescription: "सीमित फसल पहचान, मॉडल क्षमता और सामान्य जल मार्गदर्शन। यह रोग-निदान चैटबॉट नहीं है।",
    farmAnalysisTitle: "मेरे फार्म का विश्लेषण करें",
    farmAnalysisDescription: "पंजीकृत खेत के संग्रहीत पर्यावरणीय और वैज्ञानिक साक्ष्य के बारे में पूछें।",
    voiceReady: "आवाज इनपुट उपलब्ध",
    textMode: "लिखने और स्पर्श का विकल्प हमेशा उपलब्ध है",
    askUsingText: "लिखकर पूछें",
    speakQuestion: "अपना प्रश्न बोलें",
    stopListening: "सुनना बंद करें",
    noSpeech: "आवाज नहीं मिली। प्रश्न संपादित करें या लिखें।",
    recognitionInterrupted: "प्रतिलेख मिलने से पहले आवाज इनपुट रुक गया। फिर प्रयास करें या लिखें।",
    recognitionLanguageUnsupported: "इस डिवाइस पर इस भाषा की आवाज पहचान उपलब्ध नहीं है। कृपया लिखें।",
    recognitionNetworkError: "आवाज सेवा से संपर्क नहीं हो सका। कृपया प्रश्न लिखें।",
    playbackError: "ऑडियो चल नहीं पाया या बीच में रुक गया। पाठ उत्तर उपलब्ध है।",
    voiceLoading: "डिवाइस की आवाजें जांची जा रही हैं। थोड़ी देर बाद फिर प्रयास करें।",
    newQuestion: "नया प्रश्न",
    retry: "फिर प्रयास करें",
    selectFarm: "अपना फार्म चुनें",
    selectPlot: "अपना खेत/प्लॉट चुनें",
    selectBranch: "शाखा (वैकल्पिक)",
    selectRun: "पूर्ण सिमुलेशन (वैकल्पिक)",
    selectComparison: "सहेजी गई तुलना (वैकल्पिक)",
    questionPrompt: "आप क्या समझना चाहते हैं?",
    analyzeButton: "मेरे फार्म का विश्लेषण करें",
    analysisLoading: "आपके फार्म के साक्ष्य प्राप्त और जांचे जा रहे हैं…",
    analysisResult: "साक्ष्य-आधारित उत्तर",
    fieldContext: "खेत का संदर्भ",
    cropCapability: "फसल मॉडल क्षमता",
    environmentalEvidence: "पर्यावरणीय साक्ष्य",
    simulationEvidence: "वैज्ञानिक सिमुलेशन",
    comparisonEvidence: "तुलना साक्ष्य",
    supportingEvidence: "सहायक साक्ष्य देखें",
    dataFreshness: "डेटा की ताजगी",
    missingEvidence: "जानकारी उपलब्ध नहीं",
    scientificLimitations: "इस परिणाम की सीमाएं",
    expertFollowUp: "मानव विशेषज्ञ से अगला कदम",
    generationMode: "यह उत्तर कैसे तैयार हुआ",
    sourceField: "साक्ष्य क्षेत्र",
    freshnessWarning: "पुराना या बासी डेटा",
    noRegisteredFarms: "कोई पंजीकृत फार्म उपलब्ध नहीं है। विश्लेषण से पहले वास्तविक फार्म जोड़ें।",
    noPlots: "इस फार्म में कोई पंजीकृत खेत नहीं है।",
    chooseFarmPlot: "विश्लेषण पूछने से पहले फार्म और खेत चुनें।",
    analysisError: "विश्लेषण पूरा नहीं हो सका। कनेक्शन जांचें और फिर प्रयास करें।",
    noCompletedRun: "इस चयन के लिए कोई पूर्ण सिमुलेशन उपलब्ध नहीं है।",
    historicalResult: "पुराना सिमुलेशन परिणाम; यह लाइव पूर्वानुमान नहीं है।",
    unsupportedNotZero: "असमर्थित या अनुपलब्ध माप शून्य नहीं हैं।",
    llmGenerated: "सत्यापित साक्ष्य के साथ वैकल्पिक AI व्याख्या",
    deterministicGenerated: "नियम-आधारित साक्ष्य व्याख्या",
    fallbackGenerated: "AI उत्तर उपलब्ध न होने या अस्वीकार होने पर नियम-आधारित उत्तर",
    comparisonMatched: "तुलनीय इनपुट",
    comparisonNotMatched: "इनपुट मेल नहीं खाते",
    comparisonNotComparable: "तुलना संभव नहीं",
    comparisonBranches: "आधार और वैकल्पिक शाखाएं",
    comparisonRuns: "आधार और वैकल्पिक सिमुलेशन रन",
    comparisonDate: "तुलना की तारीख",
    comparisonAssumptions: "तुलना की मान्यताएं",
    noSupportedOutputs: "इस फसल के लिए मौजूदा मॉडल में कोई समर्थित संख्यात्मक परिणाम नहीं है।",
    outputCanopyCover: "फसल छत्र आवरण",
    outputBiomass: "जैवभार",
    outputYield: "उपज",
    outputEvapotranspiration: "वास्तविक वाष्पोत्सर्जन",
    outputWaterStress: "जल तनाव",
    outputIrrigation: "सिंचाई",
    freshnessFresh: "ताज़ा",
    freshnessStale: "पुराना",
    freshnessHistorical: "ऐतिहासिक",
    freshnessStaticBaseline: "स्थिर मॉडल-आधारित आधार",
    freshnessMissing: "अनुपलब्ध",
    freshnessUnavailable: "उपलब्ध नहीं",
    freshnessNewOrCached: "नया या कैश किया हुआ",
    freshnessWeatherType: "मौसम साक्ष्य",
    freshnessSoilType: "मृदा साक्ष्य",
    freshnessSnapshotType: "पर्यावरणीय स्नैपशॉट",
    freshnessInputType: "पर्यावरणीय इनपुट",
    freshnessRunType: "वैज्ञानिक सिमुलेशन रन",
    freshnessStatesType: "वैज्ञानिक सिमुलेशन स्थिति",
    freshnessComparisonType: "सिमुलेशन तुलना",
    weatherRecords: "मौसम रिकॉर्ड",
    soilProfileAvailable: "मृदा विवरण उपलब्ध",
    soilProfileMissing: "मृदा विवरण उपलब्ध नहीं",
  },
};

export function getInitialLocale(): Locale {
  const stored = typeof window !== "undefined" ? window.localStorage.getItem("terrapulse-locale") : null;
  return stored === "kn" || stored === "hi" || stored === "en" ? stored : "en";
}

export const uiTranslations: Record<Locale, Record<string, string>> = {
  en: {
    brand: "TerraPulse Decision Laboratory",
    farmWorkspace: "Farm Workspace",
    futureFold: "Future Fold",
    livingField: "Living Field",
    cropPlanning: "Crop Planning",
    calendar: "Calendar",
    agriCalendar: "Agri Calendar",
    dashboard: "Dashboard",
    getStarted: "Get Started →",
    openDecisionLab: "Open Decision Lab ◈",
    atmosphere: "Atmosphere:",
    green: "Green",
    sakura: "Sakura",
    autumn: "Autumn",
    mist: "Mist",
    heroEyebrow: "BIOPHYSICAL MODELING · REGIONAL EXTENSION · THREE.JS WORLD",
    heroTitle: "Every farm decision tested before you touch the soil",
    heroSubtitle: "TerraPulse simulates crop growth, daily moisture drawdowns, and regional climate risks into an interactive agricultural decision laboratory.",
    exploreLivingField: "Explore Real-Time Simulation →",
    exploreFutureFold: "Explore Branch Comparison →",
    readyHeading: "Ready to test your farm decisions before touching the soil?",
    readySub: "Register your farm in 60 seconds with verified coordinates and enter the interactive decision laboratory.",
    selectFarm: "Farm:",
    registerNewFarm: "+ Register Farm",
    tour: "Tour:",
    tabOverview: "Farm Workspace",
    tabAdvisory: "Advisory",
    tabObservatory: "Observatory",
    tabCropPlanning: "Crop Planning",
    tabCalendar: "Agri Calendar",
    tabFutureFold: "Future Fold",
    tabLivingField: "Living Field",
    tabSavedDecisions: "Saved Decisions",
    tabAlerts: "Alerts & Telemetry",
    tabWaterLedger: "Water Ledger",
    askAssistant: "Ask Advisory Assistant",
    askPlaceholder: "Ask about irrigation, sowing timing, disease risk or fertilizer...",
    analyzing: "Analyzing with agronomic evidence...",
    askButton: "Ask Grounded Advisor 🎙",
    saveDecision: "Verify & Save Decision",
    savingDecision: "Saving Decision to Ledger...",
  },
  kn: {
    brand: "ಟೆರಾಪಲ್ಸ್ ನಿರ್ಧಾರ ಪ್ರಯೋಗಾಲಯ",
    farmWorkspace: "ಕೃಷಿ ಕಾರ್ಯಸ್ಥಳ",
    futureFold: "ಫ್ಯೂಚರ್ ಫೋಲ್ಡ್",
    livingField: "ಸಜೀವ ಕ್ಷೇತ್ರ (3D)",
    cropPlanning: "ಬೆಳೆ ಯೋಜನೆ",
    calendar: "ಕ್ಯಾಲೆಂಡರ್",
    agriCalendar: "ಕೃಷಿ ಕ್ಯಾಲೆಂಡರ್",
    dashboard: "ನಿರ್ಧಾರ ಲ್ಯಾಬ್",
    getStarted: "ಪ್ರಾರಂಭಿಸಿ →",
    openDecisionLab: "ನಿರ್ಧಾರ ಲ್ಯಾಬ್ ತೆರೆಯಿರಿ ◈",
    atmosphere: "ವಾತಾವರಣ:",
    green: "ಹಸಿರು",
    sakura: "ಸಕುರಾ",
    autumn: "ಶರತ್ಕಾಲ",
    mist: "ಮಂಜು",
    heroEyebrow: "ಜೈವಿಕ ಭೌತಿಕ ಮಾಡೆಲಿಂಗ್ · ಪ್ರಾದೇಶಿಕ ಕೃಷಿ ವಿಸ್ತರಣೆ · 3D ಸಜೀವ ಕ್ಷೇತ್ರ",
    heroTitle: "ಮಣ್ಣನ್ನು ಮುಟ್ಟುವ ಮೊದಲು ಪ್ರತಿಯೊಂದು ಕೃಷಿ ನಿರ್ಧಾರವನ್ನು ಪರೀಕ್ಷಿಸಿ",
    heroSubtitle: "ಟೆರಾಪಲ್ಸ್ ಬೆಳೆ ಬೆಳವಣಿಗೆ, ದೈನಂದಿನ ತೇವಾಂಶ ಇಳಿಕೆ ಮತ್ತು ಹವಾಮಾನ ಅಪಾಯಗಳನ್ನು ಸಂವಾದಾತ್ಮಕ ಕೃಷಿ ನಿರ್ಧಾರ ಪ್ರಯೋಗಾಲಯದಲ್ಲಿ ಸಿಮ್ಯುಲೇಟ್ ಮಾಡುತ್ತದೆ.",
    exploreLivingField: "ನೈಜ-ಸಮಯದ ಸಿಮ್ಯುಲೇಶನ್ ಅನ್ವೇಷಿಸಿ →",
    exploreFutureFold: "ಶಾಖಾ ಹೋಲಿಕೆ ಅನ್ವೇಷಿಸಿ →",
    readyHeading: "ಮಣ್ಣನ್ನು ಮುಟ್ಟುವ ಮೊದಲು ನಿಮ್ಮ ಕೃಷಿ ನಿರ್ಧಾರಗಳನ್ನು ಪರೀಕ್ಷಿಸಲು ಸಿದ್ಧರಿದ್ದೀರಾ?",
    readySub: "ದೃಢೀಕರಿಸಿದ ನಿರ್ದೇಶಾಂಕಗಳೊಂದಿಗೆ 60 ಸೆಕೆಂಡುಗಳಲ್ಲಿ ನಿಮ್ಮ ಜಮೀನನ್ನು ನೋಂದಾಯಿಸಿ ಮತ್ತು ಸಂವಾದಾತ್ಮಕ ನಿರ್ಧಾರ ಪ್ರಯೋಗಾಲಯವನ್ನು ಪ್ರವೇಶಿಸಿ.",
    selectFarm: "ಜಮೀನು:",
    registerNewFarm: "+ ಜಮೀನು ನೋಂದಾಯಿಸಿ",
    tour: "ಪ್ರವಾಸ:",
    tabOverview: "ಕೃಷಿ ಕಾರ್ಯಸ್ಥಳ",
    tabAdvisory: "ಕೃಷಿ ಸಲಹೆಗಾರ",
    tabObservatory: "ವೀಕ್ಷಣಾಲಯ",
    tabCropPlanning: "ಬೆಳೆ ಯೋಜನೆ",
    tabCalendar: "ಕೃಷಿ ಕ್ಯಾಲೆಂಡರ್",
    tabFutureFold: "ಫ್ಯೂಚರ್ ಫೋಲ್ಡ್",
    tabLivingField: "ಸಜೀವ ಕ್ಷೇತ್ರ (3D)",
    tabSavedDecisions: "ಉಳಿಸಿದ ನಿರ್ಧಾರಗಳು",
    tabAlerts: "ಎಚ್ಚರಿಕೆಗಳು & ಟೆಲಿಮೆಟ್ರಿ",
    tabWaterLedger: "ನೀರಿನ ಲೆಡ್ಜರ್",
    askAssistant: "ಸಲಹೆ ಸಹಾಯಕರನ್ನು ಕೇಳಿ",
    askPlaceholder: "ನೀರಾವರಿ, ಬಿತ್ತನೆ ಸಮಯ, ರೋಗದ ಅಪಾಯ ಅಥವಾ ರಸಗೊಬ್ಬರದ ಬಗ್ಗೆ ಕೇಳಿ...",
    analyzing: "ಕೃಷಿ ಸಾಕ್ಷ್ಯಗಳೊಂದಿಗೆ ವಿಶ್ಲೇಷಿಸಲಾಗುತ್ತಿದೆ...",
    askButton: "ಆಧಾರಿತ ಸಲಹೆಗಾರರನ್ನು ಕೇಳಿ 🎙",
    saveDecision: "ನಿರ್ಧಾರವನ್ನು ದೃಢೀಕರಿಸಿ ಉಳಿಸಿ",
    savingDecision: "ನಿರ್ಧಾರವನ್ನು ಲೆಡ್ಜರ್‌ಗೆ ಉಳಿಸಲಾಗುತ್ತಿದೆ...",
  },
  hi: {
    brand: "टेरापल्स कृषि निर्णय प्रयोगशाला",
    farmWorkspace: "खेत कार्यक्षेत्र",
    futureFold: "फ्यूचर फोल्ड",
    livingField: "सजीव खेत (3D)",
    cropPlanning: "फसल योजना",
    calendar: "कैलेंडर",
    agriCalendar: "कृषि कैलेंडर",
    dashboard: "निर्णय लैब",
    getStarted: "आरंभ करें →",
    openDecisionLab: "निर्णय लैब खोलें ◈",
    atmosphere: "वातावरण:",
    green: "हरा",
    sakura: "सकुरा",
    autumn: "शरद",
    mist: "धुंध",
    heroEyebrow: "जैव-भौतिक मॉडलिंग · क्षेत्रीय कृषि विस्तार · 3D सजीव खेत",
    heroTitle: "मिट्टी को छूने से पहले हर कृषि निर्णय का वैज्ञानिक परीक्षण",
    heroSubtitle: "टेरापल्स फसल वृद्धि, दैनिक नमी अवशोषण और क्षेत्रीय जलवायु जोखिमों का इंटरैक्टिव कृषि निर्णय प्रयोगशाला में अनुकरण करता है।",
    exploreLivingField: "वास्तविक समय सिमुलेशन देखें →",
    exploreFutureFold: "शाखा तुलना का अन्वेषण करें →",
    readyHeading: "मिट्टी को छूने से पहले अपने कृषि निर्णयों का परीक्षण करने के लिए तैयार हैं?",
    readySub: "सत्यापित निर्देशांकों के साथ 60 सेकंड में अपने खेत को पंजीकृत करें और इंटरैक्टिव निर्णय प्रयोगशाला में प्रवेश करें।",
    selectFarm: "खेत:",
    registerNewFarm: "+ नया खेत जोड़ें",
    tour: "टूर:",
    tabOverview: "खेत कार्यक्षेत्र",
    tabAdvisory: "कृषि सलाहकार",
    tabObservatory: "पर्यावरण वेधशाला",
    tabCropPlanning: "फसल योजना",
    tabCalendar: "कृषि कैलेंडर",
    tabFutureFold: "फ्यूचर फोल्ड",
    tabLivingField: "सजीव खेत (3D)",
    tabSavedDecisions: "सहेजे गए निर्णय",
    tabAlerts: "अलर्ट और टेलीमेट्री",
    tabWaterLedger: "जल बहीखाता",
    askAssistant: "कृषि सलाहकार से पूछें",
    askPlaceholder: "सिंचाई, बुवाई का समय, रोग जोखिम या उर्वरक के बारे में पूछें...",
    analyzing: "कृषि साक्ष्यों के साथ विश्लेषण किया जा रहा है...",
    askButton: "प्रामाणिक सलाहकार से पूछें 🎙",
    saveDecision: "निर्णय सत्यापित करें और सहेजें",
    savingDecision: "बहीखाते में निर्णय सहेजा जा रहा है...",
  },
};

export function tUI(locale: Locale, key: string, fallback?: string): string {
  const dict = uiTranslations[locale] || uiTranslations.en;
  return dict[key] || uiTranslations.en[key] || fallback || key;
}
