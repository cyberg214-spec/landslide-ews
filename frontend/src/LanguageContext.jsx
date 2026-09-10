import { createContext, useContext, useState, useEffect } from 'react';
import { getTranslation } from './translations';

const LanguageContext = createContext();

export const LanguageProvider = ({ children }) => {
  const [lang, setLang] = useState(() => {
    const saved = localStorage.getItem('preferred_lang');
    // Validate: only allow en, ne, as
    return ['en', 'ne', 'as'].includes(saved) ? saved : 'en';
  });

  useEffect(() => {
    localStorage.setItem('preferred_lang', lang);
    document.documentElement.lang = lang;
  }, [lang]);

  const t = (key) => getTranslation(lang, key);

  return (
    <LanguageContext.Provider value={{ lang, setLang, t }}>
      {children}
    </LanguageContext.Provider>
  );
};

export const useLanguage = () => {
  const context = useContext(LanguageContext);
  if (!context) {
    throw new Error('useLanguage must be used within LanguageProvider');
  }
  return context;
};