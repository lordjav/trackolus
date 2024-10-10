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
// When the user clicks anywhere outside of the modal, close it

// SEARCH SCRIPT
let searchBar = document.getElementById('q');
let suggestions = document.getElementById('suggestions');

searchBar.addEventListener('focus', function () {
    suggestions.style.visibility = 'visible';
});

searchBar.addEventListener('blur', function () {
    setTimeout(function() {
        suggestions.style.visibility = 'hidden';
    }, 150)
});

//Add new notifications
let notificationsRead = [];
const evtSource = new EventSource("/notifications");
evtSource.onmessage = function(event) {
    const notificationsDiv = document.getElementById("notifications");
    const notification = JSON.parse(event.data);
    const existingNotification = document.getElementById(notification.id);
    if (existingNotification) {        
        return;
    }
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

    notificationsDiv.insertBefore(newNotification, notificationsDiv.firstChild);

    if (notification.isSeen === 0) {
        newNotification.querySelectorAll('*').forEach(function(element) {
            element.style.fontWeight = 'bold';
        });
    }    
};

evtSource.onerror = function(err) {
    console.error("EventSource failed:", err);
};

//Mark notifications as read
function markRead(container) {
    const allNotifications = container.querySelectorAll("*");
    allNotifications.forEach(function(element) {
        element.style.fontWeight = 'inherit';
    });
};

//Show/hide notifications, modals and language selection
const notifications = document.getElementById('notifications');
const notificationContainer = document.getElementById("notification-icon-container");

const languageSelect = document.getElementById("language-select-container");
const languageContainer = document.getElementById("language-container");

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

document.addEventListener("DOMContentLoaded", function() {
    notificationContainer.addEventListener("click", function(event) {
        if (notificationContainer.contains(event.target)) {
            showNotifications();
        }
    });

    languageContainer.addEventListener("click", function(event) {
        if (languageContainer.contains(event.target)) {
            if (languageSelect.style.display === 'none') {
                languageSelect.style.display = 'block';
            } else {
                languageSelect.style.display = 'none';
            }
        }
    });

    window.onclick = function(event) {
        if (!languageContainer.contains(event.target)) {
            languageSelect.style.display = 'none';
        }
        if (!notificationContainer.contains(event.target)) {
            notifications.style.display = 'none';
        }
        if (event.target == document.getElementById('add-product') || event.target == document.getElementById('transfer-products')) {
            document.getElementById('add-product').style.display = "none";
            document.getElementById('transfer-products').style.display = "none";
        }
    }
});

