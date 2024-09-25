let orderAsc = true;
let SKU_parameter = document.getElementById('SKU');
htmx.defineExtension('changeOrderSKU', {
    processNode : function(SKU_parameter) {
        orderAsc = !orderAsc;
        if (orderAsc == true) {     
            SKU_parameter.setAttribute('hx-get', '/inventory/SKU/DESC');
            SKU_parameter.innerHTML = 'SKU <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 16 16"><path fill="black" d="M13.03 8.22a.75.75 0 0 1 0 1.06l-4.25 4.25a.75.75 0 0 1-1.06 0L3.47 9.28a.75.75 0 0 1 .018-1.042a.75.75 0 0 1 1.042-.018l2.97 2.97V3.75a.75.75 0 0 1 1.5 0v7.44l2.97-2.97a.75.75 0 0 1 1.06 0"/></svg>';
            console.log('orderAsc: ' + orderAsc)
        } else {
            SKU_parameter.setAttribute('hx-get', '/inventory/SKU/ASC');
            SKU_parameter.innerHTML = 'SKU <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 16 16"><path fill="black" d="M3.47 7.78a.75.75 0 0 1 0-1.06l4.25-4.25a.75.75 0 0 1 1.06 0l4.25 4.25a.75.75 0 0 1-.018 1.042a.75.75 0 0 1-1.042.018L9 4.81v7.44a.75.75 0 0 1-1.5 0V4.81L4.53 7.78a.75.75 0 0 1-1.06 0"/></svg>';
            console.log('orderAsc: ' + orderAsc)
        };
    }
});
