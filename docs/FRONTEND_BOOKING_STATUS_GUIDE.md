# Frontend Booking Status Update Integration Guide

## Overview
This guide shows how to integrate booking status updates from your admin panel with automatic user notifications.

## API Endpoints

### 1. General Status Update (Recommended)
**Endpoint**: `POST /api/admin/bookings/update-status`

**Features**:
- ✅ Updates any booking status
- ✅ Sends user notification for "Confirmed" and "Cancelled" 
- ❌ No notification for "Pending", "Waiting", "Completed", "Expired"
- ✅ Single endpoint for all status changes

### 2. Specific Endpoints (Alternative)
- `POST /api/admin/bookings/confirm` - Only for confirming bookings
- `POST /api/admin/bookings/reject` - Only for rejecting bookings

## Frontend Implementation

### JavaScript Functions

```javascript
// Main function for updating booking status
const updateBookingStatus = async (bookingId, status, options = {}) => {
  try {
    const requestBody = {
      booking_id: bookingId,
      status: status,
      admin_notes: options.adminNotes || '',
    };

    // Add rejection reason for cancelled bookings
    if (status === 'Cancelled' && options.rejectionReason) {
      requestBody.rejection_reason = options.rejectionReason;
    }

    const response = await fetch('http://localhost:8000/api/admin/bookings/update-status', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(requestBody)
    });

    const data = await response.json();
    
    if (data.success) {
      // Show success message
      const notificationMsg = data.user_notified 
        ? ` (User notified via ${data.notification_method})`
        : ' (No user notification)';
      
      alert(`Booking status updated to ${data.booking_status}${notificationMsg}`);
      
      // Update UI
      updateBookingRowInTable(bookingId, data.booking_status);
      
      return data;
    } else {
      throw new Error(data.error || 'Failed to update booking status');
    }
  } catch (error) {
    console.error('Error updating booking status:', error);
    alert(`Failed to update booking status: ${error.message}`);
    throw error;
  }
};

// Specific helper functions for common actions
const confirmBooking = async (bookingId, adminNotes = '') => {
  return await updateBookingStatus(bookingId, 'Confirmed', { adminNotes });
};

const cancelBooking = async (bookingId, rejectionReason, adminNotes = '') => {
  return await updateBookingStatus(bookingId, 'Cancelled', { 
    rejectionReason, 
    adminNotes 
  });
};

const markBookingCompleted = async (bookingId, adminNotes = '') => {
  return await updateBookingStatus(bookingId, 'Completed', { adminNotes });
};

const resetBookingToPending = async (bookingId, adminNotes = '') => {
  return await updateBookingStatus(bookingId, 'Pending', { adminNotes });
};

// UI Helper function
const updateBookingRowInTable = (bookingId, newStatus) => {
  const row = document.querySelector(`[data-booking-id="${bookingId}"]`);
  if (row) {
    const statusCell = row.querySelector('.status-cell');
    statusCell.textContent = newStatus;
    
    // Update row styling based on status
    row.className = `booking-row status-${newStatus.toLowerCase()}`;
    
    // Update action buttons based on new status
    updateActionButtons(row, newStatus);
  }
};

const updateActionButtons = (row, status) => {
  const actionCell = row.querySelector('.action-cell');
  
  if (status === 'Confirmed') {
    actionCell.innerHTML = `
      <span class="badge badge-success">Confirmed</span>
      <button onclick="markBookingCompleted('${row.dataset.bookingId}')" class="btn btn-sm btn-info">
        Mark Completed
      </button>
    `;
  } else if (status === 'Completed') {
    actionCell.innerHTML = '<span class="badge badge-info">Completed</span>';
  } else if (status === 'Cancelled') {
    actionCell.innerHTML = `
      <span class="badge badge-danger">Cancelled</span>
      <button onclick="resetBookingToPending('${row.dataset.bookingId}')" class="btn btn-sm btn-warning">
        Reactivate
      </button>
    `;
  } else if (status === 'Pending') {
    actionCell.innerHTML = `
      <button onclick="confirmBooking('${row.dataset.bookingId}')" class="btn btn-sm btn-success">
        Confirm
      </button>
      <button onclick="showCancelModal('${row.dataset.bookingId}')" class="btn btn-sm btn-danger">
        Cancel
      </button>
    `;
  }
};
```

### HTML Structure

```html
<!-- Booking Management Table -->
<table class="table table-striped">
  <thead>
    <tr>
      <th>Booking ID</th>
      <th>Customer</th>
      <th>Property</th>
      <th>Date</th>
      <th>Status</th>
      <th>Actions</th>
    </tr>
  </thead>
  <tbody>
    <!-- Example booking row -->
    <tr class="booking-row status-waiting" data-booking-id="John-2024-12-25-Day">
      <td>John-2024-12-25-Day</td>
      <td>John Doe</td>
      <td>Sunset Farmhouse</td>
      <td>Dec 25, 2024</td>
      <td class="status-cell">Waiting</td>
      <td class="action-cell">
        <button onclick="confirmBooking('John-2024-12-25-Day')" class="btn btn-sm btn-success">
          Confirm
        </button>
        <button onclick="showCancelModal('John-2024-12-25-Day')" class="btn btn-sm btn-danger">
          Cancel
        </button>
        <div class="dropdown">
          <button class="btn btn-sm btn-secondary dropdown-toggle" data-toggle="dropdown">
            More Actions
          </button>
          <div class="dropdown-menu">
            <a class="dropdown-item" onclick="resetBookingToPending('John-2024-12-25-Day')">
              Reset to Pending
            </a>
            <a class="dropdown-item" onclick="markBookingCompleted('John-2024-12-25-Day')">
              Mark Completed
            </a>
          </div>
        </div>
      </td>
    </tr>
  </tbody>
</table>

<!-- Cancel Booking Modal -->
<div id="cancelModal" class="modal fade">
  <div class="modal-dialog">
    <div class="modal-content">
      <div class="modal-header">
        <h5 class="modal-title">Cancel Booking</h5>
        <button type="button" class="close" data-dismiss="modal">&times;</button>
      </div>
      <div class="modal-body">
        <input type="hidden" id="cancelBookingId">
        <div class="form-group">
          <label>Cancellation Reason *</label>
          <textarea id="cancellationReason" class="form-control" rows="3" 
                    placeholder="Enter reason for cancellation..." required></textarea>
        </div>
        <div class="form-group">
          <label>Admin Notes (Optional)</label>
          <textarea id="cancelAdminNotes" class="form-control" rows="2" 
                    placeholder="Internal notes..."></textarea>
        </div>
      </div>
      <div class="modal-footer">
        <button type="button" class="btn btn-secondary" data-dismiss="modal">Close</button>
        <button type="button" class="btn btn-danger" onclick="submitCancellation()">
          Cancel Booking
        </button>
      </div>
    </div>
  </div>
</div>
```

### Modal Handling Functions

```javascript
// Show cancel modal
const showCancelModal = (bookingId) => {
  document.getElementById('cancelBookingId').value = bookingId;
  document.getElementById('cancellationReason').value = '';
  document.getElementById('cancelAdminNotes').value = '';
  $('#cancelModal').modal('show');
};

// Submit cancellation
const submitCancellation = async () => {
  const bookingId = document.getElementById('cancelBookingId').value;
  const reason = document.getElementById('cancellationReason').value.trim();
  const notes = document.getElementById('cancelAdminNotes').value.trim();
  
  if (!reason) {
    alert('Please enter a cancellation reason');
    return;
  }
  
  try {
    await cancelBooking(bookingId, reason, notes);
    $('#cancelModal').modal('hide');
  } catch (error) {
    // Error already handled in cancelBooking function
  }
};

// Bulk status update (optional)
const bulkUpdateStatus = async (bookingIds, status, options = {}) => {
  const results = [];
  
  for (const bookingId of bookingIds) {
    try {
      const result = await updateBookingStatus(bookingId, status, options);
      results.push({ bookingId, success: true, result });
    } catch (error) {
      results.push({ bookingId, success: false, error: error.message });
    }
  }
  
  // Show summary
  const successful = results.filter(r => r.success).length;
  const failed = results.filter(r => !r.success).length;
  
  alert(`Bulk update completed: ${successful} successful, ${failed} failed`);
  
  return results;
};
```

## Request/Response Examples

### 1. Confirm Booking (with user notification)
```javascript
// Request
{
  "booking_id": "John-2024-12-25-Day",
  "status": "Confirmed",
  "admin_notes": "Payment verified successfully"
}

// Response
{
  "success": true,
  "message": "Booking John-2024-12-25-Day status updated to Confirmed",
  "booking_id": "John-2024-12-25-Day",
  "booking_status": "Confirmed",
  "user_notified": true,
  "notification_method": "web_chat"
}
```

### 2. Cancel Booking (with user notification)
```javascript
// Request
{
  "booking_id": "John-2024-12-25-Day",
  "status": "Cancelled",
  "rejection_reason": "Payment amount incorrect",
  "admin_notes": "Customer needs to resend correct amount"
}

// Response
{
  "success": true,
  "message": "Booking John-2024-12-25-Day status updated to Cancelled",
  "booking_id": "John-2024-12-25-Day",
  "booking_status": "Cancelled",
  "user_notified": true,
  "notification_method": "web_chat"
}
```

### 3. Mark Completed (no user notification)
```javascript
// Request
{
  "booking_id": "John-2024-12-25-Day",
  "status": "Completed",
  "admin_notes": "Customer checked out successfully"
}

// Response
{
  "success": true,
  "message": "Booking John-2024-12-25-Day status updated to Completed",
  "booking_id": "John-2024-12-25-Day",
  "booking_status": "Completed",
  "user_notified": false,
  "notification_method": null
}
```

## Status Transition Rules

| From Status | To Status | User Notification | Notes |
|-------------|-----------|-------------------|-------|
| Any | Confirmed | ✅ Yes | Sends confirmation message |
| Any | Cancelled | ✅ Yes | Sends cancellation message |
| Any | Pending | ❌ No | Silent status update |
| Any | Waiting | ❌ No | Silent status update |
| Any | Completed | ❌ No | Silent status update |
| Any | Expired | ❌ No | Silent status update |

## Error Handling

```javascript
const handleBookingError = (error, operation, bookingId) => {
  console.error(`Error ${operation} booking ${bookingId}:`, error);
  
  if (error.message.includes('Booking not found')) {
    alert('Booking not found. Please refresh the page.');
  } else if (error.message.includes('Invalid status')) {
    alert('Invalid status provided. Please check your request.');
  } else if (error.message.includes('rejection_reason')) {
    alert('Cancellation reason is required for cancelled bookings.');
  } else {
    alert(`Failed to ${operation} booking. Please try again.`);
  }
};
```

## CSS Styling (Optional)

```css
/* Status-based row styling */
.booking-row.status-pending { background-color: #fff3cd; }
.booking-row.status-waiting { background-color: #d1ecf1; }
.booking-row.status-confirmed { background-color: #d4edda; }
.booking-row.status-cancelled { background-color: #f8d7da; }
.booking-row.status-completed { background-color: #e2e3e5; }
.booking-row.status-expired { background-color: #f5c6cb; }

/* Action button styling */
.action-cell .btn {
  margin-right: 5px;
  margin-bottom: 2px;
}

.badge {
  font-size: 0.8em;
  margin-right: 5px;
}
```

## Testing

1. **Start FastAPI server**: `python -m uvicorn app.main:app --reload`
2. **Test endpoints**: Use the provided JavaScript functions
3. **Check user notifications**: Login as a user and check web chat
4. **Verify database**: Check booking status updates in database

This implementation gives you full control over booking status updates with automatic user notifications only when needed!