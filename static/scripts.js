// Get the modal
let addProductModal = document.getElementById("add-product");

// Get the button that opens the modal
let addButton = document.getElementById("add-button");

// Get the button that closes the modal
let closeModalButton = document.getElementById("close-modal-button");

// When the user clicks the button, open the modal
function showModal() {
    addProductModal.style.display = "block";
}

// When the user clicks on "x", close the modal
function closeModal() {
    addProductModal.style.display = "none";
}

// When the user clicks anywhere outside of the modal, close it
window.onclick = function(event) {
    if (event.target == addProductModal) {
        addProductModal.style.display = "none";
}}
