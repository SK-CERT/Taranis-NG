const messages_sk = {

    validations: {
        custom: {
            username: {
                required: "Vyplňte prosím prihlasovacie meno"
            },
            password: {
                required: "Heslo je povinné"
            },
            url: {
                required: "URL je povinné"
            },
            key: {
                required: "API kľúč je povinný"
            },
            name: {
                required: "Názov je povinný"
            },
            parameter: {
                required: "Parameter je povinný"
            },
            password_check: {
                required: "Heslo je povinné",
                confirmed: "Heslá sa nezhodujú"
            }
        },
    },

    login: {
        title: "Prihláste sa",
        username: "Meno",
        password: "Heslo",
        submit: "Prihlásiť",
        error: "Nesprávne meno alebo heslo"
    },

    user_menu: {
        settings: "Nastavenia profilu",
        logout: "Odhlásiť sa"
    },

    main_menu: {
        assess: "Zistiť",
        analyze: "Analyzovať",
        publish: "Publikovať",
        config: "Konfigurácia",
        dashboard: "Dashboard"
    },

    nav_menu: {
        newsitems: "Nové zistenia",
        products: "Produkty",
        publications: "Publikácie",
        recent: "Najnovšie",
        popular: "Populárne",
        favourites: "Obľúbené",
        configuration: "Konfigurácia",
        collectors_nodes: "Server zberačov údajov",
        osint_sources: "OSINT zdroje",
        collectors: "Zberače údajov",
    },

    collectors_node: {
        add_new: "Pridať nový server zberača údajov",
        add: "Pridať",
        cancel: "Zrušiť",
        validation_error: "Prosím vyplňte všetky povinné polia",
        error: "Nepodarilo sa pripojiť na zadaný server.",
        name: "Meno",
        description: "Popis",
        url: "URL",
        key: "Kľúč",
        successful: "Nový server zberača údajov bol úspešne pridaný"
    },

    osint_source: {
        add_new: "Pridať nový OSINT zdroj",
        node: "Server zberača údajov",
        collector: "Zberač údajov",
        add: "Pridať",
        cancel: "Zrušiť",
        validation_error: "Prosím vyplňte všetky povinné polia",
        error: "Nepodarilo sa vytvoriť zadaný zdroj.",
        name: "Meno",
        description: "Popis",
        last_attempt: "Posledný pokus",
        last_collected: "Posledný zber",
        successful: "Nový OSINT zdroj bol úspešne pridaný"
    },

    product: {
        add_new: "Pridať nový produkt",
        add_btn: "Pridať",
        edit: "Editovať produkt",
        save: "Uložiť",
        cancel: "Zrušiť",
        validation_error: "Prosím vyplnte všetky povinné polia",
        error: "Nemôžem vytvoriť tento produkt",
        title: "Meno",
        name: "Názov",
        description: "Popis",
        report_type: "Typ produktu",
        successful: "Nový produk bol úspešne vytvorený",
        successful_edit: "Produkt bol úspešne uložený",
        removed: "Produkt bol úspešne zmazaný",
        removed_error: "Produkt sa používa a nemôže byť zmazaný",
        preview: "Náhľad produktu",
        publish: "Publikovať produkt",
        publish_confirmation: "Ste si istý, že chcete publikovať tento produkt?",
        total_count: "Počet produktov: "
    },

    common: {
        messagebox: {
            yes: "Áno",
            no: "Nie",
            cancel: "Zrušiť",
            delete: "Ste si istý, že chcete odstrániť túto položku?",
        },
    }
};

export default messages_sk