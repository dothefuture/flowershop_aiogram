(function () {
  const tg = window.Telegram?.WebApp;
  if (tg) {
    tg.ready();
    tg.expand();
  }

  const loader = document.getElementById("loader");
  const empty = document.getElementById("empty");
  const catalogGrid = document.getElementById("catalog-grid");
  const seasonalSection = document.getElementById("seasonal-section");
  const seasonalTitle = document.getElementById("seasonal-title");
  const seasonalGrid = document.getElementById("seasonal-grid");

  function formatPrice(value) {
    return Math.round(value).toLocaleString("ru-RU") + " \u20BD";
  }

  function createCard(product, seasonal) {
    const card = document.createElement("article");
    card.className = "card";

    const img = document.createElement("img");
    img.src = product.photo_url;
    img.alt = product.name;
    img.loading = "lazy";
    card.appendChild(img);

    const body = document.createElement("div");
    body.className = "card-body";

    if (product.is_seasonal && seasonal?.enabled) {
      const tag = document.createElement("span");
      tag.className = "seasonal-tag";
      tag.textContent = seasonal.title || "СЕЗОННОЕ";
      body.appendChild(tag);
    }

    const title = document.createElement("h3");
    title.className = "card-title";
    title.textContent = product.name;
    body.appendChild(title);

    const desc = document.createElement("p");
    desc.className = "card-desc";
    desc.textContent = product.description;
    body.appendChild(desc);

    const priceRow = document.createElement("div");
    priceRow.className = "price-row";

    const price = document.createElement("span");
    price.className = "price";
    price.textContent = formatPrice(product.final_price);
    priceRow.appendChild(price);

    if (product.discount_percent > 0) {
      const old = document.createElement("span");
      old.className = "price-old";
      old.textContent = formatPrice(product.price);
      priceRow.appendChild(old);

      const badge = document.createElement("span");
      badge.className = "discount-badge";
      badge.textContent = "-" + product.discount_percent + "%";
      priceRow.appendChild(badge);
    }

    body.appendChild(priceRow);
    card.appendChild(body);
    return card;
  }

  async function loadCatalog() {
    try {
      const res = await fetch("/api/products");
      const data = await res.json();
      const seasonal = data.seasonal || {};
      const products = data.products || [];

      loader.classList.add("hidden");

      if (!products.length) {
        empty.classList.remove("hidden");
        return;
      }

      if (seasonal.enabled) {
        document.documentElement.style.setProperty(
          "--seasonal-color",
          seasonal.color || "#FF6B35"
        );
        seasonalTitle.textContent = seasonal.title || "СЕЗОННОЕ";
        const seasonalProducts = products.filter((p) => p.is_seasonal);
        if (seasonalProducts.length) {
          seasonalSection.classList.remove("hidden");
          seasonalProducts.forEach((p) => {
            seasonalGrid.appendChild(createCard(p, seasonal));
          });
        }
      }

      const regular = products.filter((p) => !p.is_seasonal);
      const catalogItems =
        regular.length > 0 ? regular : products.filter((p) => !p.is_seasonal);

      if (catalogItems.length === 0 && products.every((p) => p.is_seasonal)) {
        document.querySelector(".catalog h2").classList.add("hidden");
      } else {
        catalogItems.forEach((p) => {
          catalogGrid.appendChild(createCard(p, seasonal));
        });
      }
    } catch (err) {
      loader.textContent = "Не удалось загрузить каталог";
      console.error(err);
    }
  }

  loadCatalog();
})();
