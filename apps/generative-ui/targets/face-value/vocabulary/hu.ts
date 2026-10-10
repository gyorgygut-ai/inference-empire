export const vocabulary = {
  meta: {
    name: "Face Value",
    description: "AI arc átalakítás",
  },
  messages: {
    selectOutcome: "Válassz ki egy eredményt.",
    uploadReference: "Töltsd fel a fotódat...",
    uploadCta: "Kattints vagy húzz ide egy képet",
    outcomesAria: "Eredmények",
    userPickedOutcome: "Ezt szeretném: {title}",
    busy: "",
    working: "Dolgozom rajta...",
    busyForAWhile: "🧽 Fel lett adva a sorba. Az inferencia nem olcsó...",
    timeout: "Szerveri timeout",
    rejected: "🫷🏻 A szerver elutasította ezt a kérést.",
    sizeLimit: "A kép túl nagy",
    fulfilled: "Kész!",
    resultAlt: "Generált kép",
    download: "Letöltés",
  },
  requestSelectedOutcome: {
    assistantMessage: "Válassz ki egy eredményt.",
  },
  requestReferenceImage: {
    assistantMessage: "Töltsd fel a fotódat...",
  },
  runGenerateImage: {
    requested: {
      assistantMessage: "Kész a generálás. Jóváhagyod az inferenciát?",
      userApprove: "Generálás",
    },
    responded: {
      assistantMessage: "Jóváhagyva. Generálok...",
    },
    error: {
      assistantMessage: "Sikertelen generálás.",
    },
    streaming: {
      assistantMessage: "Dolgozom rajta...",
    },
  },
}