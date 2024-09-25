// MODAL SCRIPT
// Get the modal
let addProductModal = document.getElementById("add-product");
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