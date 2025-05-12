import React from 'react';
import './Spinner.css';

function Spinner({ size = 'medium' }) { // size can be 'small', 'medium', 'large'
  return (
    <div className={`spinner-container spinner-container-${size}`}>
      <div className={`spinner spinner-${size}`}></div>
    </div>
  );
}

export default Spinner; 