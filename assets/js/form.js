document.addEventListener("DOMContentLoaded", function () {
  const taxStatusField = document.getElementById("id_tax-tax_status");
  const visaSection = document.getElementById("visa-section");
  const visaTaxStatusField = document.getElementById("id_tax-visa_tax_status");
  const residentExtra = document.getElementById("resident-extra");

  function toggleVisaSection() {
    if (taxStatusField.value === "visa_permit") {
      visaSection.style.display = "block";
    } else {
      visaSection.style.display = "none";
      residentExtra.style.display = "none";
    }
  }

  function toggleResidentExtra() {
    if (visaTaxStatusField && visaTaxStatusField.value === "resident") {
      residentExtra.style.display = "block";
    } else {
      residentExtra.style.display = "none";
    }
  }

  if (taxStatusField) {
    // Run once on page load
    toggleVisaSection();
    // Run on change
    taxStatusField.addEventListener("change", toggleVisaSection);
  }

  if (visaTaxStatusField) {
    // Run once on page load
    toggleResidentExtra();
    // Run on change
    visaTaxStatusField.addEventListener("change", toggleResidentExtra);
  }
});

document.addEventListener("DOMContentLoaded", function () {
  // ✅ Step 2: Add/remove expense rows
  const expenseTable = document.getElementById("expense-rows");
  if (expenseTable) {
    document
      .getElementById("add-expense")
      ?.addEventListener("click", function () {
        let newRow = document.createElement("tr");
        newRow.innerHTML = `
        <td><input type="text" name="label[]" class="form-control" required></td>
        <td><input type="number" step="0.01" name="amount[]" class="form-control" required></td>
        <td><input type="text" name="currency[]" class="form-control" value="USD"></td>
        <td><input type="file" name="receipt[]" class="form-control"></td>
        <td><button type="button" class="btn btn-danger btn-sm remove-row">X</button></td>
      `;
        expenseTable.appendChild(newRow);
      });

    document.body.addEventListener("click", function (e) {
      if (e.target.classList.contains("remove-row")) {
        e.target.closest("tr").remove();
      }
    });
  }

  // ✅ Step 3: Show visa section when tax_status = visa_permit
  const taxStatusField = document.getElementById("id_tax-tax_status");
  const visaSection = document.getElementById("visa-section");
  const visaTaxStatusField = document.getElementById("id_tax-visa_tax_status");
  const residentExtra = document.getElementById("resident-extra");

  if (taxStatusField) {
    taxStatusField.addEventListener("change", function () {
      visaSection.style.display =
        this.value === "visa_permit" ? "block" : "none";

      // Reset additional fields when hiding section
      if (this.value !== "visa_permit") {
        residentExtra.style.display = "none";
      }
    });
  }

  // ✅ Show extra fields if visa_tax_status = resident
  if (visaTaxStatusField) {
    visaTaxStatusField.addEventListener("change", function () {
      residentExtra.style.display =
        this.value === "resident" ? "block" : "none";
    });
  }
});
