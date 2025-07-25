document.addEventListener("DOMContentLoaded", function () {
  // Add new expense row
  document
    .getElementById("add-expense")
    ?.addEventListener("click", function () {
      let table = document.getElementById("expense-rows");
      let newRow = document.createElement("tr");
      newRow.innerHTML = `
            <td><input type="text" name="label[]" class="form-control" required></td>
            <td><input type="number" step="0.01" name="amount[]" class="form-control" required></td>
            <td><input type="text" name="currency[]" class="form-control" value="USD"></td>
            <td><input type="file" name="receipt[]" class="form-control"></td>
            <td><button type="button" class="btn btn-danger btn-sm remove-row">X</button></td>
        `;
      table.appendChild(newRow);
    });

  // Remove expense row
  document.body.addEventListener("click", function (e) {
    if (e.target.classList.contains("remove-row")) {
      e.target.closest("tr").remove();
    }
  });

  // Show visa section if tax status = visa_permit
  const taxStatusField = document.getElementById("id_tax_status");
  const visaSection = document.getElementById("visa-section");

  if (taxStatusField) {
    taxStatusField.addEventListener("change", function () {
      visaSection.style.display =
        this.value === "visa_permit" ? "block" : "none";
    });
  }
});
