import React from 'react';
import './Header.css'; // We'll create this CSS file next

function Header() {
  return (
    <header className="app-header">
      <div className="container header-container">
        <div className="logo-title">
          {/* You can use an SVG or an image for a logo here */}
          {/* <img src="/path/to/logo.svg" alt="App Logo" className="logo-img" /> */}
          <span className="header-icon">📄</span> {/* Simple emoji icon for now */}
          <h1>Expense Manager Pro</h1>
        </div>
        <nav className="app-nav">
          {/* <a href="#">Dashboard</a>
          <a href="#">Settings</a>
          <a href="#">Profile</a> */}
          {/* Add nav links here if needed in the future */}
        </nav>
      </div>
    </header>
  );
}

export default Header; 