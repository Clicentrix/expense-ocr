import React, { useEffect } from 'react';
import './Notification.css';

function Notification({ message, type, onClose }) {
  useEffect(() => {
    if (message && onClose) {
      const timer = setTimeout(() => {
        onClose();
      }, 5000); // Auto close after 5 seconds
      return () => clearTimeout(timer);
    }
  }, [message, onClose]);

  if (!message) {
    return null;
  }

  return (
    <div className={`notification notification-${type}`}>
      <p>{message}</p>
      {onClose && (
        <button onClick={onClose} className="notification-close-btn">
          &times;
        </button>
      )}
    </div>
  );
}

export default Notification; 