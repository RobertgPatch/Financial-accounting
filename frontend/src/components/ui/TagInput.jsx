import React, { useState, useRef, useEffect } from 'react';
import { XMarkIcon } from '@heroicons/react/24/outline';

/**
 * Reusable tag chip input with autocomplete.
 * Props:
 *   - value: array of tag objects [{id, name, color, slug}]
 *   - suggestions: array of all available tags
 *   - onChange: (newTags) => void
 *   - placeholder: input placeholder
 */
export default function TagInput({ value = [], suggestions = [], onChange, placeholder = 'Add tag...' }) {
  const [input, setInput] = useState('');
  const [showDropdown, setShowDropdown] = useState(false);
  const inputRef = useRef(null);
  const containerRef = useRef(null);

  // Close dropdown on outside click
  useEffect(() => {
    const handler = (e) => {
      if (containerRef.current && !containerRef.current.contains(e.target)) {
        setShowDropdown(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const selectedIds = new Set(value.map((t) => t.id));
  const filtered = suggestions.filter(
    (s) => !selectedIds.has(s.id) && s.name.toLowerCase().includes(input.toLowerCase())
  );

  const addTag = (tag) => {
    onChange([...value, tag]);
    setInput('');
    setShowDropdown(false);
    inputRef.current?.focus();
  };

  const removeTag = (tagId) => {
    onChange(value.filter((t) => t.id !== tagId));
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Backspace' && input === '' && value.length > 0) {
      removeTag(value[value.length - 1].id);
    }
    if (e.key === 'Escape') {
      setShowDropdown(false);
    }
  };

  return (
    <div ref={containerRef} className="relative">
      <div className="flex flex-wrap gap-1 items-center border border-gray-300 rounded-lg px-2 py-1.5 min-h-[38px] focus-within:ring-2 focus-within:ring-blue-500 focus-within:border-blue-500">
        {value.map((tag) => (
          <span
            key={tag.id}
            className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium text-white"
            style={{ backgroundColor: tag.color || '#6B7280' }}
          >
            {tag.name}
            <button
              type="button"
              onClick={() => removeTag(tag.id)}
              className="hover:bg-white/20 rounded-full p-0.5"
            >
              <XMarkIcon className="h-3 w-3" />
            </button>
          </span>
        ))}
        <input
          ref={inputRef}
          type="text"
          className="flex-1 min-w-[80px] text-sm outline-none bg-transparent"
          placeholder={value.length === 0 ? placeholder : ''}
          value={input}
          onChange={(e) => {
            setInput(e.target.value);
            setShowDropdown(true);
          }}
          onFocus={() => setShowDropdown(true)}
          onKeyDown={handleKeyDown}
        />
      </div>

      {showDropdown && filtered.length > 0 && (
        <ul className="absolute z-50 mt-1 w-full bg-white border border-gray-200 rounded-lg shadow-lg max-h-40 overflow-auto">
          {filtered.map((tag) => (
            <li
              key={tag.id}
              className="flex items-center gap-2 px-3 py-2 text-sm cursor-pointer hover:bg-gray-50"
              onClick={() => addTag(tag)}
            >
              <span
                className="w-3 h-3 rounded-full flex-shrink-0"
                style={{ backgroundColor: tag.color || '#6B7280' }}
              />
              {tag.name}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
