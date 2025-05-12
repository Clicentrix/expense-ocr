import React, { useState, useRef } from 'react';
import axios from 'axios';
import Spinner from './Spinner'; // Import the spinner
import './InvoiceUploadForm.css';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000';

function InvoiceUploadForm({ onUploadSuccess, onUploadError }) {
    const [selectedFile, setSelectedFile] = useState(null);
    const [isUploading, setIsUploading] = useState(false);
    const [dragActive, setDragActive] = useState(false);
    const fileInputRef = useRef(null);

    const handleFileChange = (event) => {
        const file = event.target.files && event.target.files[0];
        if (file) {
            setSelectedFile(file);
        }
    };

    const handleSubmit = async (event) => {
        event.preventDefault();
        if (!selectedFile) {
            onUploadError('Please select a file first.');
            return;
        }

        const formData = new FormData();
        formData.append('file', selectedFile);
        // formData.append('user_id', 1); // Example user_id

        setIsUploading(true);

        try {
            const response = await axios.post(`${API_URL}/api/invoices/upload`, formData, {
                headers: {
                    'Content-Type': 'multipart/form-data',
                },
            });
            setSelectedFile(null);
            if (fileInputRef.current) {
                fileInputRef.current.value = ''; // Reset file input
            }
            if (onUploadSuccess) {
                onUploadSuccess(response.data, `File '${selectedFile.name}' processed successfully! Invoice ID: ${response.data.invoice_id}`);
            }
        } catch (error) {
            console.error('Error uploading file:', error);
            let errorMessage = 'Error uploading file.';
            if (error.response && error.response.data && error.response.data.error) {
                errorMessage = error.response.data.error;
            } else if (error.message) {
                errorMessage = error.message;
            }
            if (onUploadError) {
                onUploadError(errorMessage);
            }
        } finally {
            setIsUploading(false);
        }
    };

    // Drag and drop handlers
    const handleDrag = (e) => {
        e.preventDefault();
        e.stopPropagation();
        if (e.type === "dragenter" || e.type === "dragover") {
            setDragActive(true);
        } else if (e.type === "dragleave") {
            setDragActive(false);
        }
    };

    const handleDrop = (e) => {
        e.preventDefault();
        e.stopPropagation();
        setDragActive(false);
        if (e.dataTransfer.files && e.dataTransfer.files[0]) {
            setSelectedFile(e.dataTransfer.files[0]);
            if (fileInputRef.current) { // Sync with file input if needed or just use state
                fileInputRef.current.files = e.dataTransfer.files;
            }
        }
    };

    const openFilePicker = () => {
        fileInputRef.current.click();
    };

    return (
        <div className="upload-section card">
            <h2>Upload Your Invoice</h2>
            <p className="upload-prompt">Drag & drop your invoice file here, or click to select.</p>
            <form onSubmit={handleSubmit} onDragEnter={handleDrag} className="upload-form">
                <div 
                    className={`drop-zone ${dragActive ? 'active' : ''}`}
                    onDragEnter={handleDrag}
                    onDragLeave={handleDrag}
                    onDragOver={handleDrag}
                    onDrop={handleDrop}
                    onClick={openFilePicker} 
                >
                    <input 
                        type="file" 
                        id="invoiceFile" 
                        ref={fileInputRef}
                        onChange={handleFileChange} 
                        accept=".png,.jpg,.jpeg,.pdf" 
                        disabled={isUploading} 
                        style={{ display: 'none' }} // Hide the default input
                    />
                    {selectedFile ? (
                        <p className="file-name-display">Selected: {selectedFile.name}</p>
                    ) : (
                        <p>Drag & drop or click here</p>
                    )}
                    
                </div>
                {selectedFile && (
                     <p className="file-info">
                        <strong>Type:</strong> {selectedFile.type} | 
                        <strong>Size:</strong> {(selectedFile.size / 1024).toFixed(2)} KB
                    </p>
                )}

                <button type="submit" disabled={isUploading || !selectedFile} className="upload-button">
                    {isUploading ? (
                        <><Spinner size="small" /> Processing...</>
                    ) : (
                        'Scan Invoice'
                    )}
                </button>
            </form>
        </div>
    );
}

export default InvoiceUploadForm; 