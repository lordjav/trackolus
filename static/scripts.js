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

//::: 'Add to Cart' function :::
function addToCart() {
  let table = getElementById("purchase-cart");
  let row = table.insertRow(0);
  let cell0 = row.insertCell(0);
  let cell1 = row.insertCell(1);
  let cell2 = row.insertCell(2);
  let cell3 = row.insertCell(3);
  let cell4 = row.insertCell(4);
  let cell5 = row.insertCell(5);

  let product_id = '{{ element["id"] }}'

  cell0.innerHTML = '{{ element["SKU"] }}';
  cell1.innerHTML = '{{ element["product_name"] }}';
  cell2.innerHTML = '<input type="number" id="purchase-quantity-' + product_id + 'name="purchase-quantity" value="1" min="1" max="10">';
  cell3.innerHTML = '{{ element["sell_price"] }}';
  cell4.innerHTML = '{{ element["sell_price"] }}';
  cell5.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="30" height="30" viewBox="0 0 24 24"><path fill="none" stroke="black" stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M4 6h16l-1.58 14.22A2 2 0 0 1 16.432 22H7.568a2 2 0 0 1-1.988-1.78zm3.345-2.853A2 2 0 0 1 9.154 2h5.692a2 2 0 0 1 1.81 1.147L18 6H6zM2 6h20m-12 5v5m4-5v5"/></svg>';
}
 
