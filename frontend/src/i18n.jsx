/**
 * English / Nepali for the public pages. The staff area stays in English.
 *
 * The English sentence is its own key, so a missing translation simply shows
 * English instead of a blank. Use {name} for values: t("{n} weeks", { n: 6 }).
 *
 * Put ?lang=ne on a QR code link to open the form in Nepali.
 *
 * These translations were written carefully but not by a native speaker. Have
 * someone at the office read them once before launch.
 *
 * Country summaries, visa notes and university details come from the database
 * and are shown as entered in the Django admin.
 */
import { createContext, useContext, useEffect, useState } from "react";

const NE = {
  // Header, footer, 404
  "Free counselling": "निःशुल्क परामर्श",
  "Talk to us": "हामीसँग कुरा गर्नुहोस्",
  "Putalisadak, Kathmandu": "पुतलीसडक, काठमाडौं",
  "Sunday to Friday, 10 am – 6 pm": "आइतबार–शुक्रबार, बिहान १० – बेलुका ६",
  "A note on our figures": "हाम्रा तथ्याङ्कबारे",
  "Tuition and scholarship deadlines change. Every listing shows when we last checked it, and we ask you to confirm with the university before you pay anything.":
    "शुल्क र छात्रवृत्तिका अन्तिम मिति परिवर्तन भइरहन्छन्। हरेक सूचीमा हामीले अन्तिम पटक कहिले जाँच्यौं भन्ने देखाइएको छ। कुनै पनि रकम तिर्नुअघि विश्वविद्यालयसँग पुष्टि गर्नुहोस्।",
  "Demonstration site. All universities, fees and students shown here are sample data.":
    "नमुना वेबसाइट। यहाँ देखाइएका सबै विश्वविद्यालय, शुल्क र विद्यार्थी नमुना मात्र हुन्।",
  "Privacy": "गोपनीयता नीति",
  "We couldn't find that page": "त्यो पेज भेटिएन",
  "The link may be old or mistyped. You can still talk to a counsellor for free.":
    "लिङ्क पुरानो वा गलत टाइप भएको हुनसक्छ। तपाईं अझै पनि परामर्शदातासँग निःशुल्क कुरा गर्न सक्नुहुन्छ।",
  "Home page": "गृहपृष्ठ",
  "Loading…": "लोड हुँदैछ…",

  // Home
  "Where do you want to study?": "तपाईं कहाँ पढ्न चाहनुहुन्छ?",
  "Pick a country and we'll call you back the same day. Counselling is free, and you're not committing to anything by asking.":
    "देश छान्नुहोस्, हामी सोही दिन फोन गर्छौं। परामर्श निःशुल्क छ, र सोध्दैमा तपाईं कुनै कुरामा बाँधिनुहुन्न।",
  "{n} partner universities": "{n} साझेदार विश्वविद्यालय",
  "See universities and fees": "विश्वविद्यालय र शुल्क हेर्नुहोस्",
  "Not sure yet?": "अझै निश्चित हुनुहुन्न?",
  "Book a counselling session": "परामर्शको समय लिनुहोस्",
  "and we'll work it out together.": "र हामी सँगै निर्णय गरौं।",
  "How this works": "प्रक्रिया कसरी चल्छ",
  "Step {n}": "चरण {n}",
  "Tell us where you want to go": "कहाँ जान चाहनुहुन्छ, भन्नुहोस्",
  "One short form, or walk into the office.": "एउटा छोटो फारम भर्नुहोस्, वा सिधै कार्यालयमा आउनुहोस्।",
  "Sit down with a counsellor": "परामर्शदातासँग बसेर कुरा गर्नुहोस्",
  "Free, and no obligation to apply.": "निःशुल्क, आवेदन दिनैपर्ने बाध्यता छैन।",
  "Build your file": "आफ्नो फाइल तयार गर्नुहोस्",
  "Transcripts, funds, test scores, statement of purpose.":
    "ट्रान्सक्रिप्ट, आर्थिक स्रोत, परीक्षाको अङ्क, उद्देश्य-पत्र (SOP)।",
  "Apply and file the visa": "आवेदन र भिसा फाइल",
  "We track every deadline so you don't have to.": "हरेक अन्तिम मितिको ख्याल हामी राख्छौं।",
  "Language classes starting soon": "छिट्टै सुरु हुने भाषा कक्षाहरू",
  "IELTS, PTE and TOPIK preparation in small groups.": "सानो समूहमा IELTS, PTE र TOPIK तयारी।",
  "{test} preparation": "{test} तयारी",
  "{n} weeks": "{n} हप्ता",
  "Starts {date}": "सुरु {date}",
  "{n} seats left": "{n} सिट बाँकी",
  "The people you'll be talking to": "तपाईंसँग कुरा गर्ने हाम्रा परामर्शदाता",
  "Been refused a visa before?": "यसअघि भिसा अस्वीकृत भएको छ?",
  "It doesn't end your plans, but it does change how the next application has to be built. Tell us what happened when you fill in the form and we'll be honest with you about what's realistic.":
    "यसले तपाईंको योजना अन्त्य गर्दैन, तर अर्को आवेदन कसरी तयार गर्ने भन्ने कुरा बदलिन्छ। फारम भर्दा के भएको थियो भन्नुहोस्, के सम्भव छ भन्नेबारे हामी इमानदारीपूर्वक बताउँछौं।",
  "Start your form": "फारम सुरु गर्नुहोस्",
  "The site can't reach our servers": "वेबसाइटले हाम्रो सर्भरसँग सम्पर्क गर्न सकेन",
  "Call us on {phone} and we'll help you straight away.":
    "{phone} मा फोन गर्नुहोस्, हामी तुरुन्तै सहयोग गर्छौं।",

  // Country page
  "Studying in {name}": "{name} मा अध्ययन",
  "Talk to a {name} counsellor": "{name} का परामर्शदातासँग कुरा गर्नुहोस्",
  "What the visa asks for": "भिसाका लागि के चाहिन्छ",
  "Universities we work with": "हामीले काम गर्ने विश्वविद्यालयहरू",
  "{n} months": "{n} महिना",
  "about {amount} total": "जम्मा करिब {amount}",
  "Fees checked {date}. Confirm with the university before you pay anything.":
    "शुल्क {date} मा जाँचिएको। कुनै पनि रकम तिर्नुअघि विश्वविद्यालयसँग पुष्टि गर्नुहोस्।",
  "Scholarships": "छात्रवृत्ति",
  "Closes {date}": "अन्तिम मिति {date}",
  "We don't have a page for that destination": "त्यो गन्तव्यबारे हाम्रो पेज छैन",
  "See where we do send students": "हामी कहाँ विद्यार्थी पठाउँछौं, हेर्नुहोस्",

  // Apply form
  "Three questions. It takes about thirty seconds.": "तीन वटा प्रश्न। करिब तीस सेकेन्ड लाग्छ।",
  "Your full name": "तपाईंको पूरा नाम",
  "Phone number": "फोन नम्बर",
  "This is how a counsellor will reach you.": "परामर्शदाताले तपाईंलाई यही नम्बरमा सम्पर्क गर्नुहुनेछ।",
  "Pick more than one if you're still deciding.": "अझै निर्णय गर्दै हुनुहुन्छ भने एकभन्दा बढी छान्नुहोस्।",
  "{office} can contact me by phone about studying abroad. We keep your details private and never sell them.":
    "विदेश अध्ययनबारे {office} ले मलाई फोनमा सम्पर्क गर्न सक्छ। हामी तपाईंको विवरण गोप्य राख्छौं र कहिल्यै बेच्दैनौं।",
  "How we use your details": "हामी तपाईंको विवरण कसरी प्रयोग गर्छौं",
  "Continue": "अगाडि बढ्नुहोस्",
  "Saving…": "सुरक्षित गर्दै…",
  "A little more about you": "तपाईंको बारेमा अलि बढी",
  "All of this is optional, and we already have your contact details. Answering helps the counsellor come prepared instead of asking you on the phone.":
    "यी सबै ऐच्छिक हुन्, र तपाईंको सम्पर्क विवरण हामीसँग पहिल्यै छ। जवाफ दिनुभयो भने परामर्शदाता फोनमा सोध्नुको सट्टा तयारी गरेर आउनुहुन्छ।",
  "Highest qualification": "उच्चतम शैक्षिक योग्यता",
  "Choose one": "एउटा छान्नुहोस्",
  "+2 / A-Levels": "+2 / ए-लेभल",
  "Diploma": "डिप्लोमा",
  "Bachelor's degree": "स्नातक",
  "Master's degree": "स्नातकोत्तर",
  "Other": "अन्य",
  "Year completed (AD)": "उत्तीर्ण वर्ष (ईस्वी)",
  "Years since you last studied": "पढाइ छाडेको कति वर्ष भयो",
  "A gap is normal and it doesn't disqualify you. It just changes what we need to explain in the application.":
    "पढाइमा अन्तराल हुनु सामान्य हो, यसले तपाईंलाई अयोग्य बनाउँदैन। आवेदनमा के कुरा स्पष्ट पार्नुपर्छ भन्ने मात्र फरक पार्छ।",
  "English or Korean test": "अङ्ग्रेजी वा कोरियन भाषा परीक्षा",
  "Haven't taken one yet": "अहिलेसम्म दिएको छैन",
  "Your score": "तपाईंको अङ्क",
  "Have you applied for a student visa before?": "तपाईंले यसअघि विद्यार्थी भिसाका लागि आवेदन दिनुभएको छ?",
  "No, this is my first time": "छैन, यो पहिलो पटक हो",
  "Yes, and it was approved": "छ, र स्वीकृत भयो",
  "Yes, and it was refused": "छ, तर अस्वीकृत भयो",
  "Which country?": "कुन देश?",
  "A refusal doesn't end your plans. Knowing about it now means we build the next application to answer it directly.":
    "भिसा अस्वीकृत हुँदैमा तपाईंको योजना सकिँदैन। अहिले थाहा पाए अर्को आवेदनमा त्यसको सीधा जवाफ दिने गरी तयारी गर्न सकिन्छ।",
  "Anything else we should know?": "हामीले थाहा पाउनुपर्ने अरू केही छ?",
  "Finish": "पूरा गर्नुहोस्",
  "Skip this": "यो छोड्नुहोस्",
  "We have your details": "तपाईंको विवरण हामीलाई प्राप्त भयो",
  "A counsellor will call you on {phone} within one working day. If you'd rather not wait, the office is open Sunday to Friday, 10 am to 6 pm.":
    "एक कार्यदिनभित्र परामर्शदाताले तपाईंलाई {phone} मा फोन गर्नुहुनेछ। पर्खन चाहनुहुन्न भने कार्यालय आइतबारदेखि शुक्रबार, बिहान १० देखि बेलुका ६ बजेसम्म खुला रहन्छ।",
  "Call the office now": "अहिले नै कार्यालयमा फोन गर्नुहोस्",
  "Back to the site": "वेबसाइटमा फर्कनुहोस्",

  // Messages that come back from the server
  "Enter a phone number we can call you on.": "हामीले फोन गर्न मिल्ने नम्बर लेख्नुहोस्।",
  "Tick the box to let us contact you.": "हामीलाई सम्पर्क गर्न अनुमति दिन बाकसमा टिक लगाउनुहोस्।",
  "This field may not be blank.": "यो खाली छोड्न मिल्दैन।",
  "This field is required.": "यो भर्नु अनिवार्य छ।",
  "Something went wrong. Please try again.": "केही गडबड भयो। फेरि प्रयास गर्नुहोस्।",
  "Lots of people are using this network right now. Please call us on {phone} and we'll take your details.":
    "अहिले यो नेटवर्कबाट धेरै जनाले फारम भर्दै हुनुहुन्छ। कृपया {phone} मा फोन गर्नुहोस्, हामी तपाईंको विवरण लिन्छौं।",
};

const LangContext = createContext({ lang: "en", setLang: () => {} });

function initialLang() {
  try {
    const fromUrl = new URLSearchParams(window.location.search).get("lang");
    if (fromUrl === "ne" || fromUrl === "en") return fromUrl;
    return localStorage.getItem("banana.lang") === "ne" ? "ne" : "en";
  } catch {
    return "en";
  }
}

export function LangProvider({ children }) {
  const [lang, setLang] = useState(initialLang);

  useEffect(() => {
    document.documentElement.lang = lang;
    try {
      localStorage.setItem("banana.lang", lang);
    } catch {
      /* private browsing — the choice just won't be remembered */
    }
  }, [lang]);

  return <LangContext.Provider value={{ lang, setLang }}>{children}</LangContext.Provider>;
}

export function useT() {
  const { lang, setLang } = useContext(LangContext);
  const t = (english, vars = {}) => {
    const text = (lang === "ne" && NE[english]) || english;
    return text.replace(/\{(\w+)\}/g, (_, k) => (k in vars ? vars[k] : `{${k}}`));
  };
  // Dates in Devanagari for Nepali readers, day-month-year for English.
  const locale = lang === "ne" ? "ne-NP" : "en-GB";
  return { t, lang, setLang, locale };
}
