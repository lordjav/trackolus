// :::ADD PRODUCT MODAL:::
// Get the modal
let addProductModal = document.getElementById("add-product");

// Get the button that opens the modal
let addButton = document.getElementById("add-button");

// Get the elements that closes the modal
let closeModalButton = document.getElementById("close-modal-button");

// When the user clicks the button, open the modal
addButton.onclick = function() {
  addProductModal.style.display = "block";
}

// When the user clicks on "x", close the modal
closeModalButton.onclick = function() {
  addProductModal.style.display = "none";
}

// When the user clicks anywhere outside of the modal, close it
window.onclick = function(event) {
  if (event.target == addProductModal) {
    addProductModal.style.display = "none";
  }
}

/*// :::VIEW PRODUCT MODAL:::
// Get the modal
let viewProductModal = document.getElementById("{{ product.image_route }}");

/ Get the button that opens the modal
let addButton = document.getElementById("add-button");

// Get the elements that closes the modal
let closeModalButton = document.getElementById("close-modal-button");

// When the user clicks the button, open the modal
addButton.onclick = function() {
  modal.style.display = "block";
}

// When the user clicks on "x", close the modal
closeModalButton.onclick = function() {
  modal.style.display = "none";
}

// When the user clicks anywhere outside of the modal, close it
window.onclick = function(event) {
  if (event.target == modal) {
    modal.style.display = "none";
  }
}*/