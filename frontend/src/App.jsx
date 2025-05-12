import React, { useState, useCallback } from 'react';
import './App.css'; // App specific styles
import Header from './components/Header';
import InvoiceUploadForm from './components/InvoiceUploadForm';
import InvoiceList from './components/InvoiceList';
import Notification from './components/Notification';

function App() {
  const [refreshInvoices, setRefreshInvoices] = useState(false);
  const [notification, setNotification] = useState({ message: '', type: '' }); // type can be 'success', 'error', 'info'
  // const [selectedInvoice, setSelectedInvoice] = useState(null); // For future detail view

  const showNotification = useCallback((message, type = 'info') => {
    setNotification({ message, type });
  }, []);

  const clearNotification = useCallback(() => {
    setNotification({ message: '', type: '' });
  }, []);

  const handleUploadSuccess = (responseData, successMessage) => {
    showNotification(successMessage || 'Invoice processed successfully!', 'success');
    setRefreshInvoices(prev => !prev); // Trigger refresh in InvoiceList
  };

  const handleUploadError = (errorMessage) => {
    showNotification(errorMessage || 'An error occurred during upload.', 'error');
  };

  const handleFetchError = (errorMessage) => {
    // Only show fetch error if there isn't already an error message displayed
    if (!notification.message || notification.type !== 'error') {
      showNotification(errorMessage || 'Could not fetch invoice list.', 'error');
    }
  };

  // const handleInvoiceSelect = (invoice) => {
  //   setSelectedInvoice(invoice);
  //   // Here you could open a modal or navigate to a detail page
  //   console.log("Selected invoice:", invoice);
  //   showNotification(`Selected: ${invoice.file_name}`, 'info');
  // };

  return (
    <div className="App">
      <Header />
      <div className="container App-main-content">
        {notification.message && (
          <Notification 
            message={notification.message} 
            type={notification.type} 
            onClose={clearNotification} 
          />
        )}
        <InvoiceUploadForm 
          onUploadSuccess={handleUploadSuccess} 
          onUploadError={handleUploadError} 
        />
        <InvoiceList 
          refreshTrigger={refreshInvoices} 
          onFetchError={handleFetchError} 
          // onInvoiceSelect={handleInvoiceSelect} // Enable when detail view is implemented
        />
        {/* {selectedInvoice && (
          <div className="card mt-2">
            <h2>Selected Invoice Details (For Debug)</h2>
            <pre>{JSON.stringify(selectedInvoice, null, 2)}</pre>
          </div>
        )} */}
      </div>
    </div>
  );
}

export default App;
