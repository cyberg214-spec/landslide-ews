import { useState, useRef, useEffect } from 'react';
import { useLanguage } from '../LanguageContext';

const LanguageToggle = () => {
  const { lang, setLang } = useLanguage();
  const [open, setOpen] = useState(false);
  const dropdownRef = useRef(null);

  const languages = [
    { code: 'en', label: 'English', native: 'English', flag: '🇬🇧' },
    { code: 'hi', label: 'Hindi', native: 'हिंदी', flag: '🇮🇳' },
    { code: 'as', label: 'Assamese', native: 'অসমীয়া', flag: '🇮🇳' },
  ];

  const current = languages.find((l) => l.code === lang) || languages[0];

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSelect = (code) => {
    setLang(code);
    setOpen(false);
  };

  return (
    <div className="lang-dropdown" ref={dropdownRef}>
      <button
        className={`lang-trigger ${open ? 'open' : ''}`}
        onClick={() => setOpen(!open)}
        title="Change language"
      >
        <span className="lang-globe">🌐</span>
        <span className="lang-current">{current.native}</span>
        <span className={`lang-arrow ${open ? 'rotated' : ''}`}>▾</span>
      </button>

      {open && (
        <div className="lang-menu">
          {languages.map((l) => (
            <button
              key={l.code}
              className={`lang-option ${lang === l.code ? 'active' : ''}`}
              onClick={() => handleSelect(l.code)}
            >
              <span className="lang-flag">{l.flag}</span>
              <div className="lang-names">
                <span className="lang-native">{l.native}</span>
                <span className="lang-english">{l.label}</span>
              </div>
              {lang === l.code && <span className="lang-check">✓</span>}
            </button>
          ))}
        </div>
      )}
    </div>
  );
};

export default LanguageToggle;