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
    console.log(targetHash);
    const triggerEl = document.querySelector(
      `#v-pills-tab button[data-bs-target="${targetHash}"]`
    );
    console.log(triggerEl);
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

activateTabFromHash();

window.addEventListener("hashchange", activateTabFromHash, false);
