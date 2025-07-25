document.addEventListener("DOMContentLoaded", function () {
  // Step 2: Add/remove expense rows
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

  // Step 3: Toggle visa section
  const taxStatusField = document.getElementById("id_tax_status");
  const visaSection = document.getElementById("visa-section");
  if (taxStatusField && visaSection) {
    taxStatusField.addEventListener("change", function () {
      visaSection.style.display =
        this.value === "visa_permit" ? "block" : "none";
    });
  }
});
