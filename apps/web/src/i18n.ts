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
    ttsUnavailable: "Speech synthesis voice is not available for this language.",
    suggestedPrompts: "Suggested Questions",
    askAnother: "Ask Another Question",
    limitationsTitle: "Scientific Limitations & Biophysical Scope",
    escalationTitle: "Expert Referral Required (ICAR / KVK)",
    sourcesTitle: "Sources & Provenance",
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
    ttsUnavailable: "ಈ ಭಾಷೆಗೆ ಧ್ವನಿ ಔಟ್‌ಪುಟ್ ಲಭ್ಯವಿಲ್ಲ.",
    suggestedPrompts: "ಸೂಚಿಸಲಾದ ಪ್ರಶ್ನೆಗಳು",
    askAnother: "ಮತ್ತೊಂದು ಪ್ರಶ್ನೆ ಕೇಳಿ",
    limitationsTitle: "ವೈಜ್ಞಾನಿಕ ಮಿತಿಗಳು ಮತ್ತು ಊಹೆಗಳು",
    escalationTitle: "ತಜ್ಞರ ಸಲಹೆ ಅಗತ್ಯವಿದೆ (ಕೃಷಿ ವಿಜ್ಞಾನ ಕೇಂದ್ರ)",
    sourcesTitle: "ಮೂಲಗಳು ಮತ್ತು ಉಲ್ಲೇಖಗಳು",
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
    ttsUnavailable: "इस भाषा के लिए आवाज आउटपुट उपलब्ध नहीं है।",
    suggestedPrompts: "सुझाए गए प्रश्न",
    askAnother: "दूसरा प्रश्न पूछें",
    limitationsTitle: "वैज्ञानिक सीमाएं एवं बायोफिजिकल दायरा",
    escalationTitle: "विशेषज्ञ परामर्श आवश्यक (कृषि विज्ञान केंद्र)",
    sourcesTitle: "प्रमाणिक स्रोत एवं संदर्भ",
  },
};

export function getInitialLocale(): Locale {
  const stored = window.localStorage.getItem("terrapulse-locale");
  return stored === "kn" || stored === "hi" || stored === "en" ? stored : "en";
}
