# StockFlow Inventory Management System

StockFlow is a web-based inventory management system built with Flask and PostgreSQL.

It allows users to manage products, categories, suppliers, stock movements, activity history, and inventory reports through a simple dashboard.

## Live Demo

[Open StockFlow Live](https://stockflowinventory.onrender.com/)

## Features

- Dashboard with inventory statistics
- Product management
- Add, edit, and delete products
- Stock In and Stock Out
- Automatic Low Stock status
- Product activity history
- Category management
- Supplier management
- Inventory reports and charts
- CSV export
- PostgreSQL database
- Responsive web interface

## Technologies Used

- Python
- Flask
- PostgreSQL
- HTML
- CSS
- JavaScript
- Chart.js
- Gunicorn
- Render

## Project Structure

```text
inventory-management-system/
├── app.py
├── requirements.txt
├── README.md
├── templates/
│   ├── index.html
│   ├── products.html
│   ├── categories.html
│   ├── suppliers.html
│   ├── reports.html
│   └── sidebar.html
└── static/
    ├── style.css
    └── script.js
```

## Inventory Features

StockFlow supports product stock movements through dedicated Stock In and Stock Out actions.

Each stock movement is recorded in the product activity history, including:

- Quantity added or removed
- Previous stock quantity
- New stock quantity
- Date and time of the activity

Products with a quantity of 5 or less are automatically marked as Low Stock.

## Reports

The Reports page provides information such as:

- Total products
- Total stock
- Inventory value
- Low stock products
- Products by category
- Inventory value by category
- Product stock levels
- Stock health overview

## Database

The deployed application uses PostgreSQL for persistent data storage.

The project was initially developed with SQLite and later migrated to PostgreSQL for deployment.

## Deployment

The application is deployed using Render.

The production server uses:

```bash
gunicorn app:app
```

## Future Improvements

- Single Sign-On (SSO)
- User authentication
- Role-based access control
- Advanced inventory search and filtering
- Additional reporting features

## Author

Developed by [sabaabdullah1](https://github.com/sabaabdullah1)
