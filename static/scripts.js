// :::MODAL SCRIPT:::
// Get the modal
let modal = document.getElementById("add-product");

// Get the button that opens the modal
let addButton = document.getElementById("add-button");

// Get the elements that closes the modal
let closeModalButton = document.getElementById("close-modal-button");
let cancelModalButton = document.getElementById("cancel-modal-button");

// When the user clicks the button, open the modal
addButton.onclick = function() {
  modal.style.display = "block";
}

// When the user clicks on "x" or "Cancel", close the modal
closeModalButton.onclick = function() {
  modal.style.display = "none";
}

cancelModalButton.onclick = function() {
    modal.style.display = "none";
  }

// When the user clicks anywhere outside of the modal, close it
window.onclick = function(event) {
  if (event.target == modal) {
    modal.style.display = "none";
  }
}