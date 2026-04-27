// components/Navbar.jsx

export default function Navbar() {
  return (
    <nav className="navbar box">
      <div className="logo">CCTV Summarizer</div>

      {/* <div className="nav-links">
        <button className="nav-btn">Button 1</button>
        <button className="nav-btn">Button 2</button>
        <button className="nav-btn">Button 3</button>
      </div> */}

      <div className="user-section">
        <div className="avatar"></div>
        <span className="logo">Gauri Iyer</span>
      </div>
    </nav>
  );
}
