export default function Sidebar() {
  return (
    <div className="sidebar box" style={{ flex: 0.7 }}>
      <h3>Flags / Live Warnings</h3>
      <ul className="warning-list">
        <li>⚠️ Motion detected: Entrance</li>
        {/* <li>⚠️ Person identified: Zone A</li> */}
      </ul>
    </div>
  );
}
