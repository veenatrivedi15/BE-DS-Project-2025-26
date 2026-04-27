// components/NLQBar.jsx

// 1. We add { query, setQuery, onSearch } inside the function brackets to accept props
export default function NLQBar({ query, setQuery, onSearch }) {

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') {
      // 2. Instead of finding the ID here, we just call the function 
      // passed down from App.jsx
      onSearch(); 
    }
  };

  return (
    <div className="nlq-container box">
      <div className="search-wrapper">
        <span className="search-icon">🔍</span>
        <input 
          type="text" 
          placeholder="Type query and press Enter..." 
          className="nlq-input"
          // 3. Bind the input to the shared state
          value={query} 
          // 4. Update the shared state in App.jsx whenever the user types
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown} 
        />
      </div>
    </div>
  );
}