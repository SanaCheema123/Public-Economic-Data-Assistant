import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'

const resources = {
  en: { translation: {
    brand: 'Public Economic Data Assistant', brandAr: 'المساعد الذكي للبيانات الاقتصادية العامة',
    home: 'Overview', ask: 'Ask Assistant', insights: 'Insights', saved: 'Saved Items', settings: 'Settings',
    searchPlaceholder: 'Ask a question about Saudi economic or social data...',
    welcome: 'Welcome back, {{name}}', welcomeAr: 'مرحباً بك مجدداً',
    dashboardSub: 'Explore Saudi economic and social data through trusted sources and clear insights.',
    economicTrends: 'Economic Trends', recentQuestions: 'Recent Questions', aiSummary: 'AI Summary', verifiedSources: 'Verified Sources',
    askTitle: 'Ask the Assistant', askTitleAr: 'اطرح سؤالك على المساعد الذكي', askSub: 'Get clear, source-linked answers about Saudi economic and social data.',
    tryPrompts: 'Try These Prompts', trendingQuestions: 'Trending Questions', officialSources: 'Official Data Sources',
    insightsTitle: 'Insights', insightsTitleAr: 'الرؤى والتحليلات', insightsSub: 'Discover trends, compare indicators, and explore economic and social data.',
    period: 'Time Period', category: 'Category', all: 'All', economy: 'Economy', population: 'Population', labor: 'Labor Market', prices: 'Prices', publicFinance: 'Government & Public Finance',
    savedTitle: 'Saved Items', savedTitleAr: 'العناصر المحفوظة', savedSub: 'Your saved questions, charts, and collections — all in one place.',
    savedAnswers: 'Saved Answers', charts: 'Charts', collections: 'Collections', searchSaved: 'Search your saved items...', sortBy: 'Sort by', mostRecent: 'Most recent',
    settingsTitle: 'Settings', settingsSub: 'Manage your account and keep your experience personalized.', editProfile: 'Edit Profile', name: 'Name', email: 'Email', changePassword: 'Change Password', account: 'Account', signOut: 'Sign Out',
    startExploring: 'Start Exploring', seeDemo: 'See Demo', signIn: 'Sign In', tryItNow: 'Try It Now',
    heroKicker: 'SAUDI DATA. CLEARER TOMORROWS.', heroTitle1: 'Turn Saudi Economic Data', heroTitle2: 'Into Clear Answers',
    heroArabic: 'حوّل البيانات الاقتصادية السعودية إلى إجابات واضحة', heroDescription: 'A bilingual AI assistant that helps citizens, students, journalists and researchers understand public economic and social data through cited answers and charts.',
    trustedData: 'Trusted official data', bilingual: 'Bilingual', citedAnswers: 'Cited answers',
    featureTitle: 'Powerful Features for Everyone', featureSub: 'Everything you need to explore, understand, and make sense of Saudi economic and social data.',
    ctaTitle: 'Make Public Data Understandable for Everyone', ctaSub: 'Explore Saudi Arabia’s economic and social data with a citation-first AI assistant.',
    save: 'Save', savedDone: 'Saved', exportPdf: 'PDF', exportCsv: 'CSV', viewSource: 'View Source',
    askFollowup: 'Ask a follow-up question...', noResults: 'No results found', loading: 'Loading...',
    emptySaved: 'Nothing saved yet', emptySavedSub: 'Save an assistant answer or chart and it will appear here.',
    createCollection: 'New Collection', delete: 'Delete', openAssistant: 'Open in Assistant',
    networkError: 'The service is currently unavailable. Please try again.',
    noVerified: 'No verified dataset is available for this question.',
  }},
  ar: { translation: {
    brand: 'المساعد الذكي للبيانات الاقتصادية العامة', brandAr: 'Public Economic Data Assistant',
    home: 'نظرة عامة', ask: 'اسأل المساعد', insights: 'الرؤى', saved: 'المحفوظات', settings: 'الإعدادات',
    searchPlaceholder: 'اطرح سؤالاً عن البيانات الاقتصادية أو الاجتماعية السعودية...',
    welcome: 'مرحباً بك مجدداً، {{name}}', welcomeAr: 'Welcome back',
    dashboardSub: 'استكشف البيانات الاقتصادية والاجتماعية السعودية من خلال مصادر واضحة ومعلومات موثقة.',
    economicTrends: 'الاتجاهات الاقتصادية', recentQuestions: 'الأسئلة الأخيرة', aiSummary: 'ملخص ذكي', verifiedSources: 'المصادر الموثوقة',
    askTitle: 'اسأل المساعد', askTitleAr: 'Ask the Assistant', askSub: 'احصل على إجابات واضحة مرتبطة بالمصادر حول البيانات الاقتصادية والاجتماعية السعودية.',
    tryPrompts: 'جرّب هذه الأسئلة', trendingQuestions: 'الأسئلة الشائعة', officialSources: 'مصادر البيانات الرسمية',
    insightsTitle: 'الرؤى', insightsTitleAr: 'Insights', insightsSub: 'اكتشف الاتجاهات وقارن المؤشرات واستكشف البيانات الاقتصادية والاجتماعية.',
    period: 'الفترة الزمنية', category: 'الفئة', all: 'الكل', economy: 'الاقتصاد', population: 'السكان', labor: 'سوق العمل', prices: 'الأسعار', publicFinance: 'الحكومة والمالية العامة',
    savedTitle: 'العناصر المحفوظة', savedTitleAr: 'Saved Items', savedSub: 'أسئلتك ورسومك ومجموعاتك المحفوظة في مكان واحد.',
    savedAnswers: 'الإجابات المحفوظة', charts: 'الرسوم البيانية', collections: 'المجموعات', searchSaved: 'ابحث في العناصر المحفوظة...', sortBy: 'الترتيب', mostRecent: 'الأحدث',
    settingsTitle: 'الإعدادات', settingsSub: 'أدر حسابك وحافظ على تجربة مناسبة لك.', editProfile: 'تعديل الملف', name: 'الاسم', email: 'البريد الإلكتروني', changePassword: 'تغيير كلمة المرور', account: 'الحساب', signOut: 'تسجيل الخروج',
    startExploring: 'ابدأ الاستكشاف', seeDemo: 'شاهد العرض', signIn: 'تسجيل الدخول', tryItNow: 'جرّب الآن',
    heroKicker: 'بيانات سعودية. غد أوضح.', heroTitle1: 'حوّل البيانات الاقتصادية السعودية', heroTitle2: 'إلى إجابات واضحة',
    heroArabic: 'Turn Saudi Economic Data Into Clear Answers', heroDescription: 'مساعد ذكي ثنائي اللغة يساعد المواطنين والطلاب والصحفيين والباحثين على فهم البيانات العامة من خلال إجابات ورسوم موثقة بالمصادر.',
    trustedData: 'بيانات رسمية موثوقة', bilingual: 'عربي وإنجليزي', citedAnswers: 'إجابات موثقة',
    featureTitle: 'ميزات قوية للجميع', featureSub: 'كل ما تحتاجه لاستكشاف وفهم البيانات الاقتصادية والاجتماعية السعودية.',
    ctaTitle: 'اجعل البيانات العامة مفهومة للجميع', ctaSub: 'استكشف البيانات الاقتصادية والاجتماعية السعودية بمساعد ذكي يعتمد على المصادر.',
    save: 'حفظ', savedDone: 'تم الحفظ', exportPdf: 'PDF', exportCsv: 'CSV', viewSource: 'عرض المصدر',
    askFollowup: 'اطرح سؤالاً إضافياً...', noResults: 'لا توجد نتائج', loading: 'جارٍ التحميل...',
    emptySaved: 'لا توجد عناصر محفوظة بعد', emptySavedSub: 'احفظ إجابة أو رسماً وسيظهر هنا.',
    createCollection: 'مجموعة جديدة', delete: 'حذف', openAssistant: 'فتح في المساعد',
    networkError: 'الخدمة غير متاحة حالياً. حاول مرة أخرى.', noVerified: 'لا توجد مجموعة بيانات موثوقة لهذا السؤال.',
  }}
}

i18n.use(initReactI18next).init({
  resources,
  lng: localStorage.getItem('peda-language') || 'en',
  fallbackLng: 'en',
  interpolation: { escapeValue: false }
})

export function applyLanguage(language: 'en' | 'ar') {
  i18n.changeLanguage(language)
  localStorage.setItem('peda-language', language)
  document.documentElement.lang = language
  document.documentElement.dir = language === 'ar' ? 'rtl' : 'ltr'
}

applyLanguage((i18n.language === 'ar' ? 'ar' : 'en'))

export default i18n
