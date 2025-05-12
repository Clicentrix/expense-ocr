import React, { useState, useEffect } from 'react';
import axios from 'axios';
import Spinner from './Spinner';
import './InvoiceList.css';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000';

function InvoiceList({ refreshTrigger, onFetchError, onInvoiceSelect }) {
    const [invoices, setInvoices] = useState([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState('');

    useEffect(() => {
        const fetchInvoices = async () => {
            setIsLoading(true);
            setError('');
            try {
                const response = await axios.get(`${API_URL}/api/invoices/`);
                const sortedInvoices = response.data.sort((a, b) => 
                    new Date(b.uploaded_at) - new Date(a.uploaded_at)
                );
                setInvoices(sortedInvoices);
            } catch (err) {
                console.error('Error fetching invoices:', err);
                const errorMessage = err.response?.data?.error || 'Failed to fetch invoices.';
                setError(errorMessage);
                if (onFetchError) {
                    onFetchError(errorMessage);
                }
                setInvoices([]);
            }
            setIsLoading(false);
        };

        fetchInvoices();
    }, [refreshTrigger, onFetchError]);

    const formatDate = (dateString) => {
        if (!dateString) return 'N/A';
        try {
            return new Date(dateString).toLocaleDateString('en-CA', { // en-CA for YYYY-MM-DD format
                year: 'numeric', month: 'short', day: 'numeric'
            });
        } catch (e) { return dateString; }
    };

    const formatDateTime = (dateString) => {
        if (!dateString) return 'N/A';
        try {
            return new Date(dateString).toLocaleString('en-US', {
                year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
            });
        } catch (e) { return dateString; }
    };

    if (isLoading) {
        return <Spinner size="large" />;
    }

    if (error && invoices.length === 0) { // Only show full error if no invoices are loaded
        return <div className="message error">Error: {error}</div>;
    }

    if (invoices.length === 0) {
        return <p className="text-center mt-2">No Expense History found yet. Upload one to get started!</p>;
    }

    return (
        <div className="invoice-list-section card">
            <h2>Expense History</h2>
            {error && <div className="message error mb-1">Error refreshing list: {error}</div>} {/* Show minor error if list is already there */}
            <div className="invoice-table-container">
                <table className="invoice-table">
                    <thead>
                        <tr>
                            <th>File Name</th>
                            <th>Status</th>
                            <th>Uploaded At</th>
                            <th>Vendor</th>
                            <th>Date</th>
                            <th>Total</th>
                            {/* <th>Actions</th> */} {/* Future actions column */}
                        </tr>
                    </thead>
                    <tbody>
                        {invoices.map((invoice) => (
                            <tr key={invoice.id} onClick={() => onInvoiceSelect && onInvoiceSelect(invoice)} className="invoice-row">
                                <td data-label="File Name">{invoice.file_name}</td>
                                <td data-label="Status">
                                    <span className={`status-badge status-${invoice.status?.toLowerCase()}`}>
                                        {invoice.status}
                                    </span>
                                </td>
                                <td data-label="Uploaded At">{formatDateTime(invoice.uploaded_at)}</td>
                                <td data-label="Vendor">{invoice.vendor_name || '-'}</td>
                                <td data-label="Invoice Date">{invoice.invoice_date ? formatDate(invoice.invoice_date) : '-'}</td>
                                <td data-label="Total" className="amount-cell">
                                    {invoice.total_amount ? `$${parseFloat(invoice.total_amount).toFixed(2)}` : '-'}
                                </td>
                                {/* <td data-label="Actions">View</td> */}
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
}

export default InvoiceList; 