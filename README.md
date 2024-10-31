# Trackolus

Trackolus is a Warehouse Management System (WMS) type storage control system designed to centrally control, supervise and verify the storage of one or more warehouses. Its ease of use and simplicity in organizing information make it an appropriate tool for small and medium-sized businesses.


## Technologies used


### Frontend:

The user interface is mainly based on HTML, CSS and JavaScript. HTMX tools are used to communicate with the server and process responses. FullCalendar was used for the calendar module and some visual components use Bootstrap.



* HTML5.
* CSS 3.
* JavaScript.
* Bootstrap 5.3.3.
* HTMX 1.9.7.
* FullCalendar 6.1.15.


### Backend:

The application logic was built in Python with Flask as the framework and using Jinja2 for the rendering of the templates. The graphs were built with SQLAlchemy for queries, Pandas for structuring and Plotly for rendering. The translation of the app was based 50% on Babel and the rest on our own solutions. PDFKIT was used in the pdf document generation modules.



* Python 3.12.3.
* Flask 3.0.3.
* Babel. 2.16.0.
* Jinja2 3.1.4.
* Pandas.
* Plotly.
* PDFKIT.


### Database: 

SQLite3 through the CS50 SQL module was chosen as ORM while another part of the information management used SQLAlchemy for graph visualization and error logging.


## Installation

Since it is a web application, it only requires a browser and does not require installation, just access it via the URL to use it. It is recommended to have the latest version of the user's preferred browser to avoid incompatibility problems with the technologies used. The use of Internet Explorer 13 and earlier versions is discouraged.


## Use

When you log in, you will see 6 main sections accessible through the left sidebar:

Dashboard: a collection of graphs for visual analysis of storage in the warehouse(s). With information on income and expenses over time, products with lower stock, evolution in recent days as well as comparisons with the last week, month and quarter, etc.

Reports: access to reports based on various types of data such as products, customers, suppliers, user activity, merchandise inbound and outbound, among others. The generation of reports is offered in different formats: PDF documents, spreadsheets and CSV data files.

Inventory: List of all stored products with their respective information on SKU codes, stock, warehouse distribution, cost, images, etc. Also in this section you can access the addition of new products and the transfer of merchandise between warehouses. 

To add new products, access the drop-down menu using the button in the lower right corner, enter the product information, select a reference image and save the information. 

To transfer items between warehouses, access them through the same menu, define the origin and destination warehouse, select the items and save the transfer order.

Purchase order: with its simple interface, merchandise issue orders are added in just a few steps. Also with the option to generate quotes. To add an order, enter the customer's information (name, telephone, ID and email). If the client exists in the database, their information will be loaded into the fields automatically. Otherwise, the information will be saved in the default database. Then select the warehouse from which the merchandise will come, the products to include in the order and their quantity. You can save the purchase order or generate a pdf quote.

Inbound: to consult merchandise entry orders and their content as well as additional information, product receipt reports and the registration of new entries.

Outbound: also in list format for quick visualization of merchandise output. 

Other functions: 



* Calendar: to view orders in chronological order with the option to view by agenda, day, week and month. Access through the menu in the upper right corner. 
* Notifications: real-time recording of the most important events such as merchandise arrivals and departures, transfers between warehouses, addition and editing of new products, among others. Access through the menu in the upper right corner.
* Language: with support for English and Spanish. Selection menu in the upper right corner.


## License

This open source software is provided under the MIT license.

