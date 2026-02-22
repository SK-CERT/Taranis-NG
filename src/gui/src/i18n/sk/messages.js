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
        logout: "Odhlásiť sa",
    },

    main_menu: {
        enter: "Vložiť",
        assess: "Vyhodnotiť",
        analyze: "Analyzovať",
        publish: "Publikovať",
        config: "Konfigurácia",
        dashboard: "Dashboard",
        my_assets: "Aktíva"
    },

    nav_menu: {
        enter: "Vytvoriť novinku",
        newsitems: "Novinky",
        products: "Produkty",
        favourites: "Obľúbené",
        configuration: "Konfigurácia",
        collectors_nodes: "Inštancie zberačov",
        presenters_nodes: "Inštancie prezenterov",
        publishers_nodes: "Inštancie publikateľov",
        bots_nodes: "Inštancie robotov",
        osint_sources: "OSINT zdroje",
        osint_source_groups: "OSINT skupiny",
        publisher_presets: "Publikačné kanály",
        bot_presets: "Roboti",
        collectors: "Zberače údajov",
        report_items: "Analýzy",
        attributes: "Atribúty",
        report_types: "Typy analýz",
        product_types: "Typy produktov",
        roles: "Role",
        acls: "ACL",
        users: "Užívatelia",
        external_users: "Externí užívatelia",
        organizations: "Organizácie",
        word_lists: "Slovníky",
        asset_groups: "Skupiny aktív",
        notification_templates: "Šablóny oznámení",
        remote_access: "Vzdialený prístup",
        remote_nodes: "Vzdialené inštancie",
        local: "Lokálne",
        settings: "Nastavenia aplikácie",
        workflow: "Workflow",
        ai_providers: "AI modely",
        data_providers: "Zdroje dát",
    },

    notification: {
        close: "Zavrieť"
    },

    enter: {
        create: "Vytvoriť",
        error: "Novinku sa nepodarilo vytvoriť",
        title: "Názov",
        review: "Súhrn",
        source: "Zdroj",
        link: "Odkaz",
        content: "Obsah",
        successful: "Novinka bola úspešne vytvorená",
    },

    collectors_node: {
        add_new: "Pridať nový server zberača údajov",
        error: "Nepodarilo sa pripojiť na zadaný server.",
        name: "Meno",
        description: "Popis",
        url: "URL",
        key: "Kľúč",
        successful: "Nový server zberača údajov bol úspešne pridaný"
    },

    osint_source: {
        add_new: "Pridať nový OSINT zdroj",
        edit: "Upraviť OSINT zdroj",
        node: "Inštancia kolektoru",
        collector: "Kolektor",
        error: "Nepodarilo sa uložiť tento OSINT zdroj",
        name: "Názov",
        description: "Popis",
        last_attempt: "Posledný pokus",
        last_collected: "Posledný zber",
        last_error_message: "Posledná chyba",
        successful: "Nový OSINT zdroj bol úspešne pridaný",
        successful_edit: "OSINT zdroj bol úspešne aktualizovaný",
        removed: "OSINT zdroj bol úspešne odstránený",
        removed_error: "OSINT zdroj sa používa a nie je možné ho odstrániť",
        filter_wordlist: "Ponechať iba články, ktoré sa zhodujú aspoň s jedným slovom z vybraných zoznamov slov",
        type: "Typ",
        total_count: "Počet OSINT zdrojov: ",
        osint_source_groups: "Skupiny OSINT zdrojov",
        tooltip: {
            select_all: "Vybrať všetko",
            unselect_all: "Zrušiť výber všetkého"
        },
        notification: {
            success: "Kolektory boli úspešne pridané"
        },
        dialog_import: "Importovať OSINT zdroje",
        import: "Importovať",
        export: "Exportovať"
    },

    product: {
        add_new: "Pridať nový produkt",
        edit: "Editovať produkt",
        error: "Nemôžem vytvoriť tento produkt",
        title: "Meno",
        name: "Názov",
        description: "Popis",
        report_type: "Typ produktu",
        state: "Stav",
        successful: "Nový produk bol úspešne vytvorený",
        successful_edit: "Produkt bol úspešne uložený",
        removed: "Produkt bol úspešne zmazaný",
        removed_error: "Produkt sa používa a nemôže byť zmazaný",
        preview: "Náhľad produktu",
        publish: "Publikovať produkt",
        publish_confirmation: "Ste si istý, že chcete publikovať tento produkt?",
        publish_successful: "Produkt bol úspešne publikovaný",
        publish_failed: "Publikovanie produktu zlyhalo",
        publish_error: "Pri publikovaní produktu nastala chyba",
        no_publisher_selected: "Vyberte aspoň jedného vydavateľa",
        total_count: "Počet produktov: ",
        confirm_close: {
            message: "Máte neuložené zmeny. Naozaj chcete zavrieť tento produkt bez uloženia zmien?",
        },
        publish_unsaved: {
            title: "Publikovať neuložený produkt",
            message: "Tento produkt má neuložené zmeny. Ako chcete pokračovať?",
            close: "Zavrieť",
            save_and_publish: "Uložiť a publikovať",
            publish_only: "Publikovať bez uloženia",
        },
    },

    assess: {
        select_all_success: "{count} položiek vybraných",
        tooltip: {
            hide_review: 'Skryť náhľady noviniek',
            hide_source_link: 'Skryť odkazy na zdroje v novinkách',
            highlight_wordlist: "Zvýrazniť slová zo zoznamov slov",
            toggle_selection: "Režim výberu noviniek",
            select_all: "Vybrať všetko",
            unselect_all: "Zrušiť výber",
            filter_read: "Zobraziť prečítané novinky",
            filter_unread: "Zobraziť neprečítané novinky",
            filter_unimportant: "Zobraziť nedôležité novinky",
            filter_irrelevant: "Zobraziť irelevantné novinky",
        },
    },

    analyze: {
        select_all_success: "{count} položiek vybraných",
        tooltip: {
            toggle_selection: "Režim výberu položiek reportu",
            select_all: "Vybrať všetko",
            unselect_all: "Zrušiť výber",
            show_reports: "Zobraziť reporty obsahujúce túto položku",
        },
        reports_dialog: {
            title: "Reporty obsahujúce túto položku",
            no_reports: "Táto položka nie je v žiadnych reportoch",
            error_loading: "Chyba pri načítavaní reportov",
        },
    },

    toolbar_filter: {
        search: "Hladanie",
        all: "Všetko",
        today: "Dneska",
        this_week: "Tento týždeň",
        this_month: "Tento mesiac",
        last_7_days: "Posledných 7 dní",
        last_31_days: "Posledných 31 dní",
        custom_filter: "Vlastné filtrovanie",
    },

    settings: {
        user_settings: "Nastavenie užívateľa",
        tab_general: "Všeobecné",
        tab_wordlists: "Slovníky",
        tab_hotkeys: "Klávesové skratky",
        close_item_1: "Zavrieť (skratka 1)",
        close_item_2: "Zavrieť (skratka 2)",
        close_item_3: "Zavrieť (skratka 3)",
        collection_up_1: "Posunúť hore (skratka 1)",
        collection_up_2: "Posunúť hore (skratka 2)",
        collection_down_1: "Posunúť dole (skratka 1)",
        collection_down_2: "Posunúť dole (skratka 2)",
        show_item_1: "Zobraziť (skratka 1)",
        show_item_2: "Zobraziť (skratka 2)",
        show_item_3: "Zobraziť (skratka 3)",
        read_item: "Označit ako prečítané",
        important_item: "Označit ako dôležité",
        like_item: "Označit ako To sa mi páči",
        unlike_item: "Označit ako To sa mi nepáči",
        delete_item: "Zmazať",
        press_key: "Stlačte klávesu pre ",
        selection: "Výber",
        group: "Zoskupiť",
        ungroup: "Zrušit zoskupenie",
        new_product: "Nový produkt",
        aggregate_open: "Otvoriť zlúčenú novinku",
        enter_view_mode: "Vložte skratku pre 'view' mód",
        enter_filter_mode: "Vložte skratku pre 'filter' mód",
        dashboard_view: "Dashboard",
        analyze_view: "Analyzovať",
        publish_view: "Zverejniť",
        my_assets_view: "Aktíva",
        configuration_view: "Nastavenie",
        source_group_up: "O skupinu OSINT zdrojov vyššie",
        source_group_down: "O skupinu OSINT zdrojov nižšie",
        open_search: "Hladať",
        end: "Prejísť na koniec",
        home: "Prejísť na začiatok",
        reload: "Obnoviť",
        open_item_source: "Otevoriť zdroj položky",
        reset_keys: "Resetovať klávesové skratky",
        successful_edit: "Nastavenie bolo úspešne uložené",
        error: "Nepodarilo sa uložiť toto nastavenie!",
        boolean_error: "Hodnota musí byť buď 'True' alebo 'False'!",
        integer_error: "Hodnota musí byť platné celé číslo!",
        decimal_error: "Hodnota musí byť platné desatinné číslo!",
        default_value: "Pôvodná hodnota",
        update_value: "Upraviť hodnotu",
        description: "Popis",
        value: "Hodnota",
        updated_by: "Upravil",
        updated_at: "Upravené",
        actions: "Možnosti",
        api_key: "API klúč",
    },

    settings_enum: {
        DARK_THEME: "Tmavý motiv",
        DATE_FORMAT: 'Formát dátumu',
        HOTKEYS: "Povoliť klávesové skratky",
        UI_LANGUAGE: "Jazyk uživatelského rozhrania",
        CONTENT_DEFAULT_LANGUAGE: "Predvolený jazyk pre reporty/produkty",
        REPORT_SELECTOR_READ_ONLY: 'Otvoriť výber reportov v režime iba na čítanie',
        SPELLCHECK: "Kontrolovať pravopis",
        TAG_COLOR: "Farebný oblak značiek",
        TIME_FORMAT: 'Formát času',
    },

    error: {
        aggregate_in_use: "Niektoré vybrané novinky alebo zlúčené novinky sú už pripojené k analýze",
        server_error: "Neznámá chyba serveru...",
        validation: "Prosím vyplnte všetky povinné polia",        select_all_failed: "Zlyhalo vybratie všetkých položiek",    },

    common: {
        add: "Pridať",
        add_btn: "Pridať",
        save: "Uložiť",
        delete: "Zmazať",
        cancel: "Zrušiť",
        messagebox: {
            yes: "Áno",
            no: "Nie",
            delete: "Ste si istý, že chcete zmazať túto položku?",
            remove: "Ste si istý, že chcete odstrániť túto položku?",
        },
    },
};

export default messages_sk
