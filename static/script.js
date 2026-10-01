// ========================================
// PRODUCT MANAGEMENT
// ========================================

const modal = document.getElementById("productModal");
const addButton = document.querySelector(".add-btn");
const closeButton = document.getElementById("closeModal");
const cancelButton = document.getElementById("cancelProduct");
const productForm = document.getElementById("productForm");

const modalTitle = document.getElementById("modalTitle");
const modalDescription = document.getElementById("modalDescription");
const saveProductButton = document.getElementById("saveProductButton");

const quantityInput = document.getElementById("productQuantity");
const quantityFormGroup = document.getElementById("quantityFormGroup");


// ========================================
// PRODUCT MODAL
// ========================================

if (modal && productForm) {

    function setAddMode() {

        delete productForm.dataset.editId;

        productForm.reset();

        if (modalTitle) {
            modalTitle.textContent = "Add New Product";
        }

        if (modalDescription) {
            modalDescription.textContent =
                "Enter the product information below.";
        }

        if (saveProductButton) {
            saveProductButton.textContent = "Save Product";
        }

        if (quantityFormGroup) {
            quantityFormGroup.style.display = "";
        }

        if (quantityInput) {
            quantityInput.required = true;
            quantityInput.disabled = false;
        }
    }


    function setEditMode(button) {

        productForm.reset();

        productForm.dataset.editId = button.dataset.id;

        if (modalTitle) {
            modalTitle.textContent = "Edit Product";
        }

        if (modalDescription) {
            modalDescription.textContent =
                "Update product details. Use Stock In or Stock Out to change inventory.";
        }

        if (saveProductButton) {
            saveProductButton.textContent = "Save Changes";
        }

        document.getElementById("productName").value =
            button.dataset.name;

        document.getElementById("productCategory").value =
            button.dataset.category;

        document.getElementById("productSupplier").value =
            button.dataset.supplier || "";

        document.getElementById("productPrice").value =
            button.dataset.price;

        if (quantityFormGroup) {
            quantityFormGroup.style.display = "none";
        }

        if (quantityInput) {
            quantityInput.value = button.dataset.quantity;
            quantityInput.required = false;
            quantityInput.disabled = false;
        }

        modal.classList.add("show");
    }


    // ========================================
    // ADD PRODUCT BUTTON
    // ========================================

    if (addButton) {

        addButton.addEventListener("click", () => {

            setAddMode();

            modal.classList.add("show");
        });
    }


    // ========================================
    // CLOSE PRODUCT MODAL
    // ========================================

    function closeModal() {

        modal.classList.remove("show");

        productForm.reset();

        delete productForm.dataset.editId;

        if (quantityFormGroup) {
            quantityFormGroup.style.display = "";
        }

        if (quantityInput) {
            quantityInput.required = true;
            quantityInput.disabled = false;
        }
    }


    if (closeButton) {
        closeButton.addEventListener("click", closeModal);
    }


    if (cancelButton) {
        cancelButton.addEventListener("click", closeModal);
    }


    modal.addEventListener("click", (event) => {

        if (event.target === modal) {
            closeModal();
        }
    });


    document.addEventListener("keydown", (event) => {

        if (
            event.key === "Escape" &&
            modal.classList.contains("show")
        ) {
            closeModal();
        }
    });


    // ========================================
    // SAVE / UPDATE PRODUCT
    // ========================================

    productForm.addEventListener("submit", async (event) => {

        event.preventDefault();

        const editId = productForm.dataset.editId;

        const product = {

            name:
                document.getElementById("productName").value,

            category:
                document.getElementById("productCategory").value,

            supplier:
                document.getElementById("productSupplier").value,

            price:
                document.getElementById("productPrice").value,

            quantity:
                quantityInput
                    ? quantityInput.value
                    : 0
        };


        let url = "/api/products";
        let method = "POST";


        if (editId) {

            url = `/api/products/${editId}`;
            method = "PUT";
        }


        try {

            const response =
                await fetch(
                    url,
                    {
                        method: method,

                        headers: {
                            "Content-Type":
                                "application/json"
                        },

                        body:
                            JSON.stringify(product)
                    }
                );


            const result =
                await response.json();


            if (
                response.ok &&
                result.success
            ) {

                closeModal();

                window.location.href =
                    "/products";

            } else {

                alert(
                    result.message ||
                    "Unable to save product."
                );
            }

        } catch (error) {

            console.error(
                "Error saving product:",
                error
            );

            alert(
                "Unable to save product."
            );
        }
    });


    // ========================================
    // EDIT BUTTONS
    // ========================================

    const editButtons =
        document.querySelectorAll(".edit-btn");


    editButtons.forEach(button => {

        button.addEventListener("click", () => {

            setEditMode(button);
        });
    });

}


// ========================================
// STOCK IN / STOCK OUT
// ========================================

const stockModal =
    document.getElementById("stockModal");

const stockForm =
    document.getElementById("stockForm");

const stockModalTitle =
    document.getElementById("stockModalTitle");

const stockModalDescription =
    document.getElementById("stockModalDescription");

const stockAmountLabel =
    document.getElementById("stockAmountLabel");

const stockAmount =
    document.getElementById("stockAmount");

const currentStock =
    document.getElementById("currentStock");

const saveStockButton =
    document.getElementById("saveStockButton");

const closeStockModalButton =
    document.getElementById("closeStockModal");

const cancelStockButton =
    document.getElementById("cancelStock");


// ========================================
// OPEN STOCK MODAL
// ========================================

function openStockModal(button, type) {

    if (!stockModal || !stockForm) {
        return;
    }


    const productId =
        button.dataset.id;

    const productName =
        button.dataset.name;

    const quantity =
        button.dataset.quantity;


    stockForm.dataset.productId =
        productId;

    stockForm.dataset.type =
        type;


    if (stockAmount) {
        stockAmount.value = "";
    }


    if (currentStock) {

        const unitWord =
            Number(quantity) === 1
                ? "unit"
                : "units";

        currentStock.textContent =
            `${quantity} ${unitWord}`;
    }


    if (type === "in") {

        if (stockModalTitle) {
            stockModalTitle.textContent =
                "Stock In";
        }

        if (stockModalDescription) {
            stockModalDescription.textContent =
                `Add inventory to ${productName}.`;
        }

        if (stockAmountLabel) {
            stockAmountLabel.textContent =
                "Quantity to Add";
        }

        if (saveStockButton) {
            saveStockButton.textContent =
                "Add Stock";
        }

    } else {

        if (stockModalTitle) {
            stockModalTitle.textContent =
                "Stock Out";
        }

        if (stockModalDescription) {
            stockModalDescription.textContent =
                `Remove inventory from ${productName}.`;
        }

        if (stockAmountLabel) {
            stockAmountLabel.textContent =
                "Quantity to Remove";
        }

        if (saveStockButton) {
            saveStockButton.textContent =
                "Remove Stock";
        }
    }


    stockModal.classList.add("show");


    if (stockAmount) {
        stockAmount.focus();
    }
}


// ========================================
// STOCK IN BUTTONS
// ========================================

document
    .querySelectorAll(".stock-in-btn")
    .forEach(button => {

        button.addEventListener(
            "click",
            () => {

                openStockModal(
                    button,
                    "in"
                );
            }
        );
    });


// ========================================
// STOCK OUT BUTTONS
// ========================================

document
    .querySelectorAll(".stock-out-btn")
    .forEach(button => {

        button.addEventListener(
            "click",
            () => {

                openStockModal(
                    button,
                    "out"
                );
            }
        );
    });


// ========================================
// OPEN STOCK IN FROM DASHBOARD
// ========================================

const stockUrlParams =
    new URLSearchParams(
        window.location.search
    );

const stockProductId =
    stockUrlParams.get("stock");


if (stockProductId) {

    const matchingStockButton =
        Array.from(
            document.querySelectorAll(
                ".stock-in-btn"
            )
        ).find(
            button =>
                button.dataset.id ===
                stockProductId
        );


    if (matchingStockButton) {

        openStockModal(
            matchingStockButton,
            "in"
        );
    }
}


// ========================================
// CLOSE STOCK MODAL
// ========================================

function closeStockModal() {

    if (!stockModal) {
        return;
    }


    stockModal.classList.remove("show");


    if (stockForm) {

        stockForm.reset();

        delete stockForm.dataset.productId;
        delete stockForm.dataset.type;
    }
}


if (closeStockModalButton) {

    closeStockModalButton.addEventListener(
        "click",
        closeStockModal
    );
}


if (cancelStockButton) {

    cancelStockButton.addEventListener(
        "click",
        closeStockModal
    );
}


if (stockModal) {

    stockModal.addEventListener(
        "click",
        (event) => {

            if (event.target === stockModal) {
                closeStockModal();
            }
        }
    );
}


// ========================================
// SAVE STOCK MOVEMENT
// ========================================

if (stockForm) {

    stockForm.addEventListener(
        "submit",
        async (event) => {

            event.preventDefault();


            const productId =
                stockForm.dataset.productId;

            const type =
                stockForm.dataset.type;

            const amount =
                parseInt(
                    stockAmount.value,
                    10
                );


            if (
                !productId ||
                !["in", "out"].includes(type)
            ) {
                return;
            }


            if (
                !Number.isInteger(amount) ||
                amount <= 0
            ) {

                alert(
                    "Please enter a quantity greater than zero."
                );

                return;
            }


            try {

                if (saveStockButton) {
                    saveStockButton.disabled = true;
                }


                const response =
                    await fetch(
                        `/api/products/${productId}/stock`,
                        {
                            method: "POST",

                            headers: {
                                "Content-Type":
                                    "application/json"
                            },

                            body:
                                JSON.stringify({
                                    type: type,
                                    amount: amount
                                })
                        }
                    );


                const result =
                    await response.json();


                if (
                    response.ok &&
                    result.success
                ) {

                    closeStockModal();

                    window.location.href =
                        "/products";

                } else {

                    alert(
                        result.message ||
                        "Unable to update stock."
                    );
                }

            } catch (error) {

                console.error(
                    "Error updating stock:",
                    error
                );

                alert(
                    "Unable to update stock."
                );

            } finally {

                if (saveStockButton) {
                    saveStockButton.disabled = false;
                }
            }
        }
    );
}


// ========================================
// PRODUCT STOCK HISTORY
// ========================================

const historyModal =
    document.getElementById("historyModal");

const historyProductName =
    document.getElementById(
        "historyProductName"
    );

const productHistoryList =
    document.getElementById(
        "productHistoryList"
    );

const closeHistoryModalButton =
    document.getElementById(
        "closeHistoryModal"
    );

const closeHistoryButton =
    document.getElementById(
        "closeHistoryButton"
    );


function closeHistoryModal() {

    if (historyModal) {
        historyModal.classList.remove("show");
    }
}


// ========================================
// HISTORY BUTTONS
// ========================================

document
    .querySelectorAll(".history-btn")
    .forEach(button => {

        button.addEventListener(
            "click",
            async () => {

                if (
                    !historyModal ||
                    !productHistoryList
                ) {
                    return;
                }


                const productId =
                    button.dataset.id;

                const productName =
                    button.dataset.name;


                if (historyProductName) {

                    historyProductName.textContent =
                        `${productName} activity and stock movements.`;
                }


                productHistoryList.innerHTML = `
                    <div class="history-loading">
                        Loading history...
                    </div>
                `;


                historyModal.classList.add("show");


                try {

                    const response =
                        await fetch(
                            `/api/products/${productId}/history`
                        );


                    const result =
                        await response.json();


                    if (
                        !response.ok ||
                        !result.success
                    ) {

                        productHistoryList.innerHTML = `
                            <div class="history-empty">
                                Unable to load product history.
                            </div>
                        `;

                        return;
                    }


                    if (
                        !result.history ||
                        result.history.length === 0
                    ) {

                        productHistoryList.innerHTML = `
                            <div class="history-empty">
                                No activity recorded for this product yet.
                            </div>
                        `;

                        return;
                    }


                    productHistoryList.innerHTML =
                        result.history
                            .map(activity => {

                                let activityClass =
                                    "history-updated";


                                if (
                                    activity.action ===
                                    "Product Added"
                                ) {

                                    activityClass =
                                        "history-added";

                                } else if (
                                    activity.action ===
                                    "Product Restocked" ||
                                    activity.action ===
                                    "Stock In"
                                ) {

                                    activityClass =
                                        "history-restocked";

                                } else if (
                                    activity.action ===
                                    "Stock Out"
                                ) {

                                    activityClass =
                                        "history-stock-out";

                                } else if (
                                    activity.action ===
                                    "Product Deleted"
                                ) {

                                    activityClass =
                                        "history-deleted";
                                }


                                return `
                                    <div class="history-item">

                                        <div
                                            class="history-dot ${activityClass}"
                                        ></div>

                                        <div class="history-info">

                                            <div class="history-top">

                                                <span class="history-action">
                                                    ${escapeHtml(activity.action)}
                                                </span>

                                                <span class="history-time">
                                                    ${escapeHtml(activity.time)}
                                                </span>

                                            </div>

                                            <div class="history-details">
                                                ${escapeHtml(activity.details)}
                                            </div>

                                        </div>

                                    </div>
                                `;
                            })
                            .join("");

                } catch (error) {

                    console.error(
                        "Error loading product history:",
                        error
                    );


                    productHistoryList.innerHTML = `
                        <div class="history-empty">
                            Unable to load product history.
                        </div>
                    `;
                }
            }
        );
    });


// ========================================
// HISTORY MODAL EVENTS
// ========================================

if (closeHistoryModalButton) {

    closeHistoryModalButton.addEventListener(
        "click",
        closeHistoryModal
    );
}


if (closeHistoryButton) {

    closeHistoryButton.addEventListener(
        "click",
        closeHistoryModal
    );
}


if (historyModal) {

    historyModal.addEventListener(
        "click",
        (event) => {

            if (event.target === historyModal) {
                closeHistoryModal();
            }
        }
    );
}


// ========================================
// ESCAPE KEY
// ========================================

document.addEventListener(
    "keydown",
    (event) => {

        if (event.key !== "Escape") {
            return;
        }


        if (
            stockModal &&
            stockModal.classList.contains("show")
        ) {
            closeStockModal();
        }


        if (
            historyModal &&
            historyModal.classList.contains("show")
        ) {
            closeHistoryModal();
        }
    }
);


// ========================================
// SAFE HTML OUTPUT
// ========================================

function escapeHtml(value) {

    const element =
        document.createElement("div");

    element.textContent =
        value == null
            ? ""
            : String(value);

    return element.innerHTML;
}

// ========================================
// MORE ACTIONS MENU
// ========================================

const moreButtons =
    document.querySelectorAll(".more-btn");


// Close all open menus
function closeMoreMenus() {

    document
        .querySelectorAll(".more-dropdown.show")
        .forEach(menu => {

            menu.classList.remove("show");

        });
}


// Open / close menu
moreButtons.forEach(button => {

    button.addEventListener(
        "click",
        (event) => {

            event.stopPropagation();

            const menu =
                button.nextElementSibling;

            const isOpen =
                menu.classList.contains("show");

            closeMoreMenus();

            if (!isOpen) {
                menu.classList.add("show");
            }

        }
    );

});


// Clicking inside the dropdown should not
// immediately close it
document
    .querySelectorAll(".more-dropdown")
    .forEach(menu => {

        menu.addEventListener(
            "click",
            (event) => {

                event.stopPropagation();

            }
        );

    });


// Close menu when clicking anywhere else
document.addEventListener(
    "click",
    () => {

        closeMoreMenus();

    }
);


// Close menu with Escape
document.addEventListener(
    "keydown",
    (event) => {

        if (event.key === "Escape") {
            closeMoreMenus();
        }

    }
);


// ========================================
// DELETE PRODUCTS
// ========================================

document
    .querySelectorAll(".delete-btn")
    .forEach(button => {

        button.addEventListener(
            "click",
            async () => {

                const confirmDelete =
                    confirm(
                        "Are you sure you want to delete this product?"
                    );


                if (!confirmDelete) {
                    return;
                }


                try {

                    const response =
                        await fetch(
                            `/api/products/${button.dataset.id}`,
                            {
                                method: "DELETE"
                            }
                        );


                    const result =
                        await response.json();


                    if (
                        response.ok &&
                        result.success
                    ) {

                        window.location.reload();

                    } else {

                        alert(
                            result.message ||
                            "Unable to delete product."
                        );
                    }

                } catch (error) {

                    console.error(
                        "Error deleting product:",
                        error
                    );

                    alert(
                        "Unable to delete product."
                    );
                }
            }
        );
    });


// ========================================
// PRODUCT SEARCH
// ========================================

const searchInput =
    document.getElementById("searchInput");


if (searchInput) {

    searchInput.addEventListener(
        "input",
        () => {

            const value =
                searchInput.value
                    .toLowerCase()
                    .trim();


            document
                .querySelectorAll(".product-row")
                .forEach(row => {

                    const text =
                        row.textContent
                            .toLowerCase();


                    row.style.display =
                        text.includes(value)
                            ? ""
                            : "none";
                });
        }
    );
}


// ========================================
// INVENTORY REPORTS
// ========================================

async function loadReports() {

    const categoryCanvas =
        document.getElementById("categoryChart");

    const valueCanvas =
        document.getElementById("valueChart");

    const stockCanvas =
        document.getElementById("stockChart");

    const stockHealthCanvas =
        document.getElementById("stockHealthChart");


    // Only run on Reports page
    if (
        !categoryCanvas &&
        !valueCanvas &&
        !stockCanvas &&
        !stockHealthCanvas
    ) {
        return;
    }


    try {

        const response =
            await fetch("/api/reports");


        if (!response.ok) {

            throw new Error(
                "Unable to load report data."
            );
        }


        const data =
            await response.json();


        // ========================================
        // SUMMARY CARDS
        // ========================================

        const inventoryValue =
            document.getElementById(
                "reportInventoryValue"
            );

        const totalStock =
            document.getElementById(
                "reportTotalStock"
            );

        const totalProducts =
            document.getElementById(
                "reportTotalProducts"
            );

        const lowStock =
            document.getElementById(
                "reportLowStock"
            );


        if (inventoryValue) {

            inventoryValue.textContent =
                new Intl.NumberFormat(
                    "en-US",
                    {
                        style: "currency",
                        currency: "USD"
                    }
                ).format(
                    data.inventory_value || 0
                );
        }


        if (totalStock) {

            totalStock.textContent =
                Number(
                    data.total_stock || 0
                ).toLocaleString();
        }


        if (totalProducts) {

            totalProducts.textContent =
                Number(
                    data.total_products || 0
                ).toLocaleString();
        }


        if (lowStock) {

            lowStock.textContent =
                Number(
                    data.low_stock_count || 0
                ).toLocaleString();
        }


        // ========================================
        // CHART DEFAULTS
        // ========================================

        if (typeof Chart === "undefined") {
            return;
        }


        Chart.defaults.font.family =
            "Arial, Helvetica, sans-serif";

        Chart.defaults.color =
            "#708084";


        const tealColors = [
            "#167d7f",
            "#3f9292",
            "#65a8a6",
            "#88bcba",
            "#a9cfcc",
            "#c7e0de",
            "#527f80",
            "#79aaa9"
        ];


        // ========================================
        // PRODUCTS BY CATEGORY
        // ========================================

        if (categoryCanvas) {

            new Chart(
                categoryCanvas,
                {
                    type: "doughnut",

                    data: {

                        labels:
                            data.category_names,

                        datasets: [{
                            data:
                                data.category_counts,

                            backgroundColor:
                                tealColors,

                            borderColor:
                                "#ffffff",

                            borderWidth: 3,

                            hoverOffset: 5
                        }]
                    },

                    options: {

                        responsive: true,

                        maintainAspectRatio: false,

                        cutout: "65%",

                        plugins: {

                            legend: {

                                position: "bottom",

                                labels: {

                                    usePointStyle: true,

                                    pointStyle:
                                        "circle",

                                    padding: 18,

                                    boxWidth: 8,

                                    boxHeight: 8
                                }
                            },

                            tooltip: {

                                callbacks: {

                                    label:
                                        function(context) {

                                            const value =
                                                context.raw;

                                            return (
                                                `${context.label}: ` +
                                                `${value} ` +
                                                (
                                                    value === 1
                                                        ? "product"
                                                        : "products"
                                                )
                                            );
                                        }
                                }
                            }
                        }
                    }
                }
            );
        }


        // ========================================
        // INVENTORY VALUE BY CATEGORY
        // ========================================

        if (valueCanvas) {

            new Chart(
                valueCanvas,
                {
                    type: "bar",

                    data: {

                        labels:
                            data.category_value_names,

                        datasets: [{

                            label:
                                "Inventory Value",

                            data:
                                data.category_values,

                            backgroundColor:
                                "#4d9999",

                            borderColor:
                                "#167d7f",

                            borderWidth: 1,

                            borderRadius: 6,

                            borderSkipped: false
                        }]
                    },

                    options: {

                        responsive: true,

                        maintainAspectRatio: false,

                        plugins: {

                            legend: {
                                display: false
                            },

                            tooltip: {

                                callbacks: {

                                    label:
                                        function(context) {

                                            return (
                                                "Value: " +
                                                new Intl.NumberFormat(
                                                    "en-US",
                                                    {
                                                        style:
                                                            "currency",

                                                        currency:
                                                            "USD"
                                                    }
                                                ).format(
                                                    context.raw
                                                )
                                            );
                                        }
                                }
                            }
                        },

                        scales: {

                            x: {

                                grid: {
                                    display: false
                                },

                                border: {
                                    display: false
                                }
                            },

                            y: {

                                beginAtZero: true,

                                border: {
                                    display: false
                                },

                                grid: {
                                    color:
                                        "#edf2f2"
                                },

                                ticks: {

                                    callback:
                                        function(value) {

                                            return "$" +
                                                Number(
                                                    value
                                                ).toLocaleString();
                                        }
                                }
                            }
                        }
                    }
                }
            );
        }


        // ========================================
        // STOCK LEVELS BY PRODUCT
        // ========================================

        if (stockCanvas) {

            const stockColors =
                data.product_quantities.map(
                    quantity =>
                        quantity <= 5
                            ? "#d49a45"
                            : "#6cb5b2"
                );


            new Chart(
                stockCanvas,
                {
                    type: "bar",

                    data: {

                        labels:
                            data.product_names,

                        datasets: [{

                            label:
                                "Units in Stock",

                            data:
                                data.product_quantities,

                            backgroundColor:
                                stockColors,

                            borderWidth: 0,

                            borderRadius: 6,

                            borderSkipped: false
                        }]
                    },

                    options: {

                        responsive: true,

                        maintainAspectRatio: false,

                        plugins: {

                            legend: {
                                display: false
                            },

                            tooltip: {

                                callbacks: {

                                    label:
                                        function(context) {

                                            const quantity =
                                                context.raw;

                                            return (
                                                `${quantity} ` +
                                                (
                                                    quantity === 1
                                                        ? "unit"
                                                        : "units"
                                                )
                                            );
                                        }
                                }
                            }
                        },

                        scales: {

                            x: {

                                grid: {
                                    display: false
                                },

                                border: {
                                    display: false
                                },

                                ticks: {

                                    maxRotation: 45,

                                    minRotation: 0
                                }
                            },

                            y: {

                                beginAtZero: true,

                                border: {
                                    display: false
                                },

                                grid: {
                                    color:
                                        "#edf2f2"
                                },

                                ticks: {
                                    precision: 0
                                }
                            }
                        }
                    }
                }
            );
        }


        // ========================================
        // STOCK HEALTH
        // ========================================

        if (stockHealthCanvas) {

            new Chart(
                stockHealthCanvas,
                {
                    type: "doughnut",

                    data: {

                        labels:
                            data.stock_health_labels,

                        datasets: [{

                            data:
                                data.stock_health_counts,

                            backgroundColor: [
                                "#5ca39a",
                                "#d49a45"
                            ],

                            borderColor:
                                "#ffffff",

                            borderWidth: 3,

                            hoverOffset: 5
                        }]
                    },

                    options: {

                        responsive: true,

                        maintainAspectRatio: false,

                        cutout: "65%",

                        plugins: {

                            legend: {

                                position: "bottom",

                                labels: {

                                    usePointStyle: true,

                                    pointStyle:
                                        "circle",

                                    padding: 18,

                                    boxWidth: 8,

                                    boxHeight: 8
                                }
                            },

                            tooltip: {

                                callbacks: {

                                    label:
                                        function(context) {

                                            const value =
                                                context.raw;

                                            return (
                                                `${context.label}: ` +
                                                `${value} ` +
                                                (
                                                    value === 1
                                                        ? "product"
                                                        : "products"
                                                )
                                            );
                                        }
                                }
                            }
                        }
                    }
                }
            );
        }


    } catch (error) {

        console.error(
            "Error loading reports:",
            error
        );
    }
}


loadReports();