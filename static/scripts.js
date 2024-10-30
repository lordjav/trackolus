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

// Add new notifications. Adapted with help from AI tools
let notificationsRead = [];
const evtSource = new EventSource("/notifications");
evtSource.onmessage = function(event) {
    const notificationsDiv = document.getElementById("notifications");
    const notification = JSON.parse(event.data);
    const existingNotification = document.getElementById(notification.id);
    if (existingNotification) {        
        return;
    }
    // Create new notification, title, date and message
    const newNotification = document.createElement("div");
    newNotification.id = notification.id;
    newNotification.className = "notification";

    const title = document.createElement("h3");
    title.textContent = notification.title;

    const date = document.createElement("p");
    date.textContent = new Date(notification.date).toLocaleString();

    const message = document.createElement("p");
    message.style.whiteSpace = 'pre-line';
    message.textContent = notification.message;

    newNotification.appendChild(title);
    newNotification.appendChild(date);
    newNotification.appendChild(message);

    // Add notification to the top of the list
    notificationsDiv.insertBefore(newNotification, notificationsDiv.firstChild);
    // For new notifications, make the text bold
    if (notification.isSeen === 0) {
        newNotification.querySelectorAll('*').forEach(function(element) {
            element.style.fontWeight = 'bold';
        });
    }    
};

evtSource.onerror = function(err) {
    console.error("EventSource failed:", err);
};

// Mark notifications as read
function markRead(container) {
    const allNotifications = container.querySelectorAll("*");
    allNotifications.forEach(function(element) {
        element.style.fontWeight = 'inherit';
    });
};

// Show/hide notifications, modals and language selection
const notifications = document.getElementById('notifications');
const notificationContainer = document.getElementById("notification-icon-container");
const notificationContainerAux = document.getElementById("notification-icon-container-aux");

const languageSelect = document.getElementById("language-select-container");
const languageContainer = document.getElementById("language-container");
const languageContainerAux = document.getElementById("language-container-aux");

// Show notifications and send request to mark them as read
function showNotifications() {    
    if (notifications.style.display === 'none') {        
        notifications.style.display = 'block';
        notifications.querySelectorAll('.notification').forEach(function(element) {
            notificationsRead.push(parseInt(element.id));
        });
        notifications.dispatchEvent(new CustomEvent("markRead"));
    } else {
        notifications.style.display = 'none';
    }
};
// After page load, add event listeners to show notification and language containers
document.addEventListener("DOMContentLoaded", function() {
    // If click on notification icon, relocate and show notifications (Wide screens)
    notificationContainer.addEventListener("click", function(event) {
        if (notificationContainer.contains(event.target)) {
            notificationContainer.appendChild(notifications);
            notifications.classList.toggle('notifications-small', false);
            showNotifications();
        }
    });

    // If click on notification icon, relocate and show notifications (Small screens)
    notificationContainerAux.addEventListener('click', function(event) {
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
        if (!notificationContainer.contains(event.target) && !notificationContainerAux.contains(event.target)) {
            notifications.style.display = 'none';
        }
        if (event.target.classList.contains('modal-window')) {
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
    toolsModal.style.display = "block";
    toolsModal.style.zIndex = 10;
    toolsBar.style.display = "flex";
    toolsBar.style.zIndex = 11;

}
function closeSidebar() {
    toolsModal.style.display = "none";
    toolsModal.style.zIndex = -3;
    toolsBar.style.display = "none";
    toolsBar.style.zIndex = 1;
}


