// MODAL SCRIPT
// When the user clicks the button, open the modal
function showModal(id) {
    let modal = document.getElementById(id);
    modal.style.display = "block";
}
// When the user clicks on "x", close the modal
function closeModal(id) {
    let modal = document.getElementById(id);
    modal.style.display = "none";
}

// SEARCH SCRIPT
let searchBar = document.getElementById('q');
let suggestions = document.getElementById('suggestions');

searchBar.addEventListener('focus', function () {
    suggestions.style.display = 'block';
});

// Hide suggestions when the search bar loses focus
searchBar.addEventListener('blur', function () {
    setTimeout(function() {
        suggestions.style.display = 'none';
    }, 150)
});

// NOTIFICATIONS SCRIPT
// Change the notification icon when there are unread notifications
const readIndicator = document.getElementById('read-indicator');
document.addEventListener('htmx:afterSettle', (event) => {
    // If notifications are shown and there are unread notifications, change the notification icon
    if (event.target.id === 'notifications' && document.getElementsByClassName('unread').length > 0) {
        readIndicator.classList.remove('hidden');
    }
});

// Show/hide notifications, modals and language selection

const notificationContainer = document.getElementById("notification-icon-container");
const notificationContainerAux = document.getElementById("notification-icon-container-aux");
const notificationIcon = document.getElementById("notification-icon");
const notificationIconAux = document.getElementById("notification-icon-aux");

const languageSelect = document.getElementById("language-select-container");
const languageContainer = document.getElementById("language-container");
const languageContainerAux = document.getElementById("language-container-aux");

// Show notifications and send request to mark them as read
let notificationsRead = [];
function showNotifications() {
    const notifications = document.getElementById('notifications');
    if (notifications.style.display === 'none') {        
        notifications.style.display = 'block';
        // Make a list of notifications to mark as read
        notifications.querySelectorAll('.notification').forEach(function(element) {
            notificationsRead.push(parseInt(element.id));
        });
        // Create a custom event to be used by HTMX to make POST request
        notifications.dispatchEvent(new CustomEvent("markRead"));
        // Change the notification icon to read
        readIndicator.classList.add('hidden');
    } else {
        notifications.style.display = 'none';
    }
};

// After page load, add event listeners to show notification and language containers
document.addEventListener("DOMContentLoaded", function() {
    // If click on notification icon, relocate and show notifications (Wide screens)
    notificationContainer.addEventListener("click", function(event) {
        const notifications = document.getElementById('notifications');
        if (notificationContainer.contains(event.target)) {
            notificationContainer.appendChild(notifications);
            notifications.classList.toggle('notifications-small', false);
            showNotifications();
        }
    });
    // If click on notification icon, relocate and show notifications (Small screens)
    notificationContainerAux.addEventListener('click', function(event) {
        const notifications = document.getElementById('notifications');
        if (notificationContainerAux.contains(event.target)) {
            toolsModal.appendChild(notifications);
            notifications.classList.toggle('notifications-small', true);
            showNotifications();
        }
    });
    // If click on language icon, relocate and show language selection (Wide screens)
    languageContainer.addEventListener("click", function(event) {
        if (languageContainer.contains(event.target)) {
            languageContainer.appendChild(languageSelect);
            languageSelect.classList.toggle('language-small', false);
            if (languageSelect.style.display === 'none') {
                languageSelect.style.display = 'block';
            } else {
                languageSelect.style.display = 'none';
            }
        }
    });
    // If click on language icon, relocate and show language selection (Small screens)
    languageContainerAux.addEventListener("click", function(event) {
        if (languageContainerAux.contains(event.target)) {
            toolsModal.appendChild(languageSelect);
            languageSelect.classList.toggle('language-small', true);
            if (languageSelect.style.display === 'none') {
                languageSelect.style.display = 'block';
            } else {
                languageSelect.style.display = 'none';
            }
        }
    });
    // If click outside the notification or language containers or modal window, hide them
    window.onclick = function(event) {
        if (!languageContainer.contains(event.target) && !languageContainerAux.contains(event.target)) {
            languageSelect.style.display = 'none';
        }
        const notifications = document.getElementById('notifications');
        if (!notificationContainer.contains(event.target) && !notificationContainerAux.contains(event.target)) {
            notifications.style.display = 'none';
        }
        if (event.target.classList.contains('modal-window')) {
            notificationIcon.appendChild(readIndicator);
            event.target.style.display = "none";
        }
    }
});

// Sidebar modal in small screens
const sidebarModal = document.getElementById('sidebar-modal');
const sidebar = document.getElementById('sidebar-aux');

function showSidebar() {
    sidebarModal.style.display = "block";
    sidebarModal.style.zIndex = 10;
    sidebar.style.display = "block";
    sidebar.style.zIndex = 11;
}
function closeSidebar() {
    sidebarModal.style.display = "none";
    sidebarModal.style.zIndex = -3;
    sidebar.style.display = "none";
    sidebar.style.zIndex = 1;
}

// Tools modal in small screens
const toolsModal = document.getElementById('tools-modal');
const toolsBar = document.getElementById('tools-modal-content');
const notifAux = document.getElementById('notifications-aux');

function showToolsbar() {
    notificationIconAux.appendChild(readIndicator);
    toolsModal.style.display = "block";
    toolsModal.style.zIndex = 10;
    toolsBar.style.display = "flex";
    toolsBar.style.zIndex = 11;

}
function closeToolsbar() {
    notificationIcon.appendChild(readIndicator);
    toolsModal.style.display = "none";
    toolsModal.style.zIndex = -3;
    toolsBar.style.display = "none";
    toolsBar.style.zIndex = 1;
}
