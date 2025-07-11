const triggerTabList = document.querySelectorAll("#v-pills-tab button");
triggerTabList.forEach((triggerEl) => {
  const tabTrigger = new bootstrap.Tab(triggerEl);

  triggerEl.addEventListener("click", (event) => {
    event.preventDefault();
    tabTrigger.show();
  });
});

const activateTabFromHash = () => {
  if (window.location.hash) {
    let targetHash = window.location.hash;

    const triggerEl = document.querySelector(
      `#v-pills-tab button[data-bs-target="${targetHash}"]`
    );

    if (triggerEl) {
      let tabInstance = bootstrap.Tab.getInstance(triggerEl);
      if (!tabInstance) {
        tabInstance = new bootstrap.Tab(triggerEl);
      }
      tabInstance.show();
    } else {
      console.log(`No tab found for hash: ${targetHash}`);
    }
  }
};

document.querySelectorAll('[data-bs-toggle="pill"]').forEach((tabButton) => {
  tabButton.addEventListener("shown.bs.tab", (event) => {
    const targetSelector = event.target.getAttribute("data-bs-target");
    if (targetSelector) {
      // Remove the leading # to get clean ID
      const cleanId = targetSelector.replace(/^#/, "");
      // Update the URL hash without adding a new history entry
      history.replaceState(null, null, "#" + cleanId);
    }
  });
});

activateTabFromHash();

window.addEventListener("hashchange", activateTabFromHash, false);
