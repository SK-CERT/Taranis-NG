const messages_sk = {
    validations: {
        messages: {
            _default: "Prosím, vyplňte požadované pole",
        },

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
            },
            collector_node: {
                required: "Vyberte inštanciu kolektora",
            },
            file: {
                required: "Súbor je povinný",
            },
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
        config: "Nastavenie",
        dashboard: "Dashboard",
        my_assets: "Aktíva"
    },

    dashboard: {
        assess: {
            tagcloud: "Tagcloud pre najnovšie získané novinky",
            total: "noviniek celkom",
        },
        collect: {
            title: "Kolektory",
            status: "Stav aktivity kolektorov",
            pending: "Kolektory sú momentálne pozastavené",
            last_attempt: "Posledné úspešné spustenie skončilo",
        },
        analyze: {
            status: "Stavy analýz",
            report_items: "",
            total: "analýz celkom",
        },
        publish: {
            status: "Stavy publikácií",
            products: "",
            total: "publikácií celkom",
        },
        about: {
            title: "O aplikácii",
            total: "záznamov celkom",
            version: "Verzia",
        },
    },

    nav_menu: {
        enter: "Vytvoriť novinku",
        newsitems: "Novinky",
        products: "Publikácie",
        favourites: "Obľúbené",
        configuration: "Nastavenie",
        collectors_nodes: "Inštancie kolektorov",
        presenters_nodes: "Inštancie prezenterov",
        publishers_nodes: "Inštancie vydavateľov",
        bots_nodes: "Inštancie robotov",
        osint_sources: "OSINT zdroje",
        osint_source_groups: "OSINT skupiny",
        publisher_presets: "Publikačné kanály",
        bot_presets: "Roboti",
        collectors: "Kolektory",
        report_items: "Analýzy",
        attributes: "Atribúty",
        report_types: "Typy analýz",
        product_types: "Typy publikácií",
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
        error: "Nepodarilo sa vytvoriť novinku",
        title: "Názov",
        review: "Súhrn",
        source: "Zdroj",
        link: "Odkaz",
        content: "Obsah",
        successful: "Novinka bola úspešne vytvorená",
    },

    card_item: {
        title: "Názov",
        created: "Vytvorené",
        updated: "Aktualizované",
        collected: "Získané",
        published: "Publikované",
        source: "Zdroj",
        node: "Inštancia",
        description: "Popis",
        in_analyze: "Analýza prebieha",
        url: "URL",
        name: "Názov",
        username: "Meno používateľa",
        aggregated_items: "Zlúčené novinky",
        last_seen: "Naposledy videné",
    },

    organization: {
        add_new: "Pridať novú organizáciu",
        edit: "Upraviť organizáciu",
        error: "Nepodarilo sa vytvoriť organizáciu",
        name: "Názov",
        description: "Popis",
        street: "Ulica",
        city: "Mesto",
        zip: "PSČ",
        country: "Krajina",
        successful: "Nová organizácia bola úspešne pridaná",
        successful_edit: "Organizácia bola úspešne upravená",
        removed: "Organizácia bola úspešne odstránená",
        removed_error: "Organizácia sa používa a nie je možné ju odstrániť",
        total_count: "Počet organizácií: ",
    },

    user: {
        add_new: "Pridať nového používateľa",
        edit: "Upraviť používateľa",
        error: "Nepodarilo sa vytvoriť používateľa",
        username: "Meno používateľa",
        name: "Meno",
        successful: "Nový používateľ bol úspešne pridaný",
        successful_edit: "Používateľ bol úspešne upravený",
        removed: "Používateľ bol úspešne odstránený",
        removed_error: "Používateľ sa používa a nie je možné ho odstrániť",
        organizations: "Organizácie",
        roles: "Role",
        permissions: "Oprávnenia",
        total_count: "Počet používateľov: ",
        password: "Heslo",
        password_check: "Zadajte heslo znova",
    },

    collectors_node: {
        add_new: "Pridať nový inštanciu kolektora",
        edit: "Upraviť inštanciu kolektora",
        error: "Nepodarilo sa pripojiť na zadaný server",
        name: "Meno",
        description: "Popis",
        url: "URL",
        key: "Kľúč",
        successful: "Nová inštancia kolektora bola úspešne pridaná",
        successful_edit: "Inštancia kolektora bola úspešne upravená",
        removed: "Inštancia kolektora bola úspešne odstránená",
        removed_error: "Inštancia kolektora sa používa a nie je možné ju odstrániť",
        total_count: "Počet inštancií kolektorov: ",
    },

    osint_source: {
        add_new: "Pridať nový OSINT zdroj",
        edit: "Upraviť OSINT zdroj",
        node: "Inštancia kolektoru",
        collector: "Kolektor",
        error: "Nepodarilo sa uložiť OSINT zdroj",
        name: "Názov",
        description: "Popis",
        last_attempt: "Posledný pokus",
        last_collected: "Posledný zber",
        last_error_message: "Posledná chyba",
        successful: "Nový OSINT zdroj bol úspešne pridaný",
        successful_edit: "OSINT zdroj bol úspešne upravený",
        removed: "OSINT zdroj bol úspešne odstránený",
        removed_error: "OSINT zdroj sa používa a nie je možné ho odstrániť",
        filter_wordlist: "Ponechať iba články obsahujúce aspoň jedno slovo zo zvolených slovníkov",
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

    osint_source_group: {
        add_new: "Pridať novú skupinu OSINT zdrojov",
        edit: "Upraviť skupinu OSINT zdrojov",
        error: "Nepodarilo sa uložiť skupinu OSINT zdrojov",
        description: "Popis",
        successful: "Nová skupina OSINT zdrojov bola úspešne pridaná",
        successful_edit: "Skupina OSINT zdrojov bola úspešne upravená",
        removed: "Skupina OSINT zdrojov bola úspešne odstránená",
        removed_error: "Skupina OSINT zdrojov sa používa a nie je možné ju odstrániť",
        title: "Názov",
        osint_sources: "OSINT zdroje",
        total_count: "Počet skupín OSINT zdrojov: ",
        default_group: "Nezaradené",
        default_group_description: "Predvolená skupina pre nezaradené OSINT zdroje",
        all: "Všetky zdroje",
    },

    role: {
        add_new: "Pridať novú rolu",
        edit: "Upraviť rolu",
        error: "Nepodarilo sa uložiť rolu.",
        name: "Názov",
        description: "Popis",
        successful: "Nová rola bola úspešne pridaná",
        successful_edit: "Rola bola úspešne aktualizovaná",
        removed: "Rola bola úspešne odstránená",
        removed_error: "Rola sa používa a nie je možné ju odstrániť",
        title: "Názov",
        permissions: "Oprávnenia",
        total_count: "Počet rolí: ",
    },

    acl: {
        full_title: "Zoznamy riadenia prístupu",
        add_new: "Pridať nové ACL",
        edit: "Upraviť ACL",
        error: "Nepodarilo sa uložiť ACL.",
        name: "Názov",
        description: "Popis",
        item_type: "Typ položky",
        item: "Položka",
        everyone: "Všetci",
        see: "Zobraziť",
        access: "Prístup",
        modify: "Upraviť",
        successful: "Nové ACL bolo úspešne pridané",
        successful_edit: "ACL bolo úspešne aktualizované",
        removed: "ACL bolo úspešne odstránené",
        removed_error: "ACL sa používa a nie je možné ho odstrániť",
        roles: "Role",
        users: "Používatelia",
        total_count: "Počet ACL: ",
    },

    publisher_preset: {
        add_new: "Pridať nový publikačný kanál",
        edit: "Upraviť publikačný kanál",
        node: "Inštancia vydavateľa",
        publisher: "Vydavateľ",
        error: "Nepodarilo sa vytvoriť tento kanál.",
        name: "Názov",
        description: "Popis",
        use_for_notifications: "Použiť pre všetky globálne notifikácie",
        successful: "Nový publikačný kanál bol úspešne pridaný",
        successful_edit: "Publikačný kanál bol úspešne aktualizovaný",
        removed: "Publikačný kanál bol úspešne odstránený",
        removed_error: "Publikačný kanál sa používa a nie je možné ho odstrániť",
        total_count: "Počet publikačných kanálov: ",
    },

    product_type: {
        add_new: "Pridať nový typ publikácie",
        edit: "Upraviť typ publikácie",
        node: "Inštancia prezentéra",
        presenter: "Prezentér",
        error: "Nepodarilo sa vytvoriť typ publikácie.",
        name: "Názov",
        description: "Popis",
        successful: "Nový typ publikácie bol úspešne pridaný",
        successful_edit: "Typ publikácie bol úspešne aktualizovaný",
        removed: "Typ publikácie bol úspešne odstránený",
        removed_error: "Typ publikácie sa používa a nie je možné ho odstrániť",
        total_count: "Počet typov publikácií: ",
        help: "Popis parametrov šablóny",
        close: "Zavrieť",
        choose_report_type: "Vyberte typ analýzy pre zobrazenie popisu parametrov",
        report_items: "Položky analýz",
        report_items_object: {
            name: "Názov",
            name_prefix: "Prefix názvu",
            type: "Typ položky analýzy",
        },
        news_items: "Novinky",
        news_items_object: {
            title: "Názov",
            review: "Súhrn",
            content: "Obsah",
            author: "Autor",
            source: "Zdroj",
            link: "Odkaz",
            collected: "Dátum zberu",
            published: "Dátum publikovania",
        },
    },

    presenters_node: {
        add_new: "Pridať novú inštanciu prezentéra",
        edit: "Upraviť inštanciu prezentéra",
        error: "Nepodarilo sa pripojiť k inštancii prezentéra.",
        name: "Názov",
        description: "Popis",
        url: "URL",
        key: "Kľúč",
        successful: "Nová inštancia prezentéra bola úspešne pridaná",
        successful_edit: "Inštancia prezentéra bola úspešne aktualizovaná",
        removed: "Inštancia prezentéra bola úspešne odstránená",
        removed_error: "Inštancia prezentéra sa používa a nie je možné ju odstrániť",
        total_count: "Počet inštancií prezentérov: ",
    },

    publishers_node: {
        add_new: "Pridať novú inštanciu vydavateľa",
        edit: "Upraviť inštanciu vydavateľa",
        error: "Nepodarilo sa pripojiť k inštancii vydavateľa.",
        name: "Názov",
        description: "Popis",
        url: "URL",
        key: "Kľúč",
        successful: "Nová inštancia vydavateľa bola úspešne pridaná",
        successful_edit: "Inštancia vydavateľa bola úspešne aktualizovaná",
        removed: "Inštancia vydavateľa bola úspešne odstránená",
        removed_error: "Inštancia vydavateľa sa používa a nie je možné ju odstrániť",
        total_count: "Počet inštancií vydavateľov: ",
    },

    bots_node: {
        add_new: "Pridať novú inštanciu robota",
        edit: "Upraviť inštanciu robota",
        error: "Nepodarilo sa pripojiť k inštancii robota.",
        name: "Názov",
        description: "Popis",
        url: "URL",
        key: "Kľúč",
        successful: "Nová inštancia robota bola úspešne pridaná",
        successful_edit: "Inštancia robota bola úspešne aktualizovaná",
        removed: "Inštancia robota bola úspešne odstránená",
        removed_error: "Inštancia robota sa používa a nie je možné ju odstrániť",
        total_count: "Počet inštancií robotov: ",
    },

    bot_preset: {
        add_new: "Pridať nového robota",
        edit: "Upraviť robota",
        node: "Inštancia robota",
        bot: "Robot",
        error: "Nepodarilo sa vytvoriť robota.",
        name: "Názov",
        description: "Popis",
        successful: "Nový robota bol úspešne pridaný",
        successful_edit: "Robot bol úspešne aktualizovaný",
        removed: "Robota bol úspešne odstránený",
        removed_error: "Robot sa používa a nie je možné ho odstrániť",
        total_count: "Počet robotov: ",
    },

    attribute: {
        add_new: "Pridať nový atribút",
        add_constant: "Pridať konštantu",
        edit_constant: "Upraviť konštantu",
        edit: "Upraviť atribút",
        add_attachment: "Pridať prílohu",
        add_value: "Pridať hodnotu",
        select_attachment: "Vybrať prílohu",
        select_file: "Vybrať súbor",
        error: "Nepodarilo sa vytvoriť atribút",
        name: "Názov",
        description: "Popis",
        type: "Typ",
        validator: "Validátor",
        validator_parameter: "Parameter validátora",
        default_value: "Predvolená hodnota",
        successful: "Nový atribút bol úspešne pridaný",
        successful_edit: "Atribút bol úspešne aktualizovaný",
        removed: "Atribút bol úspešne odstránený",
        removed_error: "Atribút sa používa a nie je možné ho odstrániť",
        value: "Hodnota",
        value_text: "Text hodnoty",
        tlp_clear: "TLP:CLEAR",
        tlp_green: "TLP:GREEN",
        tlp_amber: "TLP:AMBER",
        tlp_amber_strict: "TLP:AMBER+STRICT",
        tlp_red: "TLP:RED",
        attribute_parameters: "Parametre atribútu",
        attribute_constants: "Konštanty atribútu",
        import_from_csv: "Import z CSV",
        new_constant: "Nová konštanta",
        attribute: "Typ atribútu",
        attributes: "Atribúty",
        new_attribute: "Nový atribút",
        min_occurrence: "Minimálny výskyt",
        max_occurrence: "Maximálny výskyt",
        total_count: "Počet atribútov: ",
        import: "Import",
        load_csv_file: "Načítať CSV súbor",
        file_has_header: "Súbor obsahuje hlavičku",
        search: "Vyhľadávanie",
        reload_cpe: "Znovu načítať CPE slovník",
        reload_cve: "Znovu načítať CVE slovník",
        reload_cwe: "Znovu načítať CWE slovník",
        delete_existing: "Odstrániť všetky existujúce hodnoty",
        select_enum: "Vybrať konštantnú hodnotu",
        reloading: "Znovu načítavam slovník...",
        status: "Stav",
        select_date: "Vybrať dátum",
        select_time: "Vybrať čas",
        select_datetime: "Vybrať dátum a čas",
        done: "Hotovo",
        ai_provider: "AI model",
        ai_prompt: "AI prompt",
        add_attribute: "Pridať atribút",
        edit_attribute: "Upraviť atribút",
    },

    cvss_calculator: {
        title: "CVSS Calculator 3.1",
        base_score: "Base Score",
        attack_vector: "Attack Vector (AV)",
        attack_complexity: "Attack Complexity (AC)",
        privileges_required: "Privileges Required (PR)",
        user_interaction: "User Interaction (UI)",
        scope: "Scope (S)",
        confidentiality: "Confidentiality (C)",
        integrity: "Integrity (I)",
        availability: "Availability (A)",

        temporal_score: "Temporal Score",
        exploitability_code_maturity: "Exploitability Code Maturity (E)",
        remediation_level: "Remediation Level (RL)",
        report_confidence: "Report Confidence (RC)",

        environmental_score: "Environmental Score",
        confidentiality_requirement: "Confidentiality Requirement (CR)",
        integrity_requirement: "Integrity Requirement (IR)",
        availability_requirement: "Availability Requirement (AR)",
        modified_attack_vector: "Modified Attack Vector (MAV)",
        modified_attack_complexity: "Modified Attack Complexity (MAC)",
        modified_privileges_required: "Modified Privileges Required (MPR)",
        modified_user_interaction: "Modified User Interaction (MUI)",
        modified_scope: "Modified Scope (MS)",
        modified_confidentiality: "Modified Confidentiality (MC)",
        modified_integrity: "Modified Integrity (MI)",
        modified_availability: "Modified Availability (MA)",

        network: "Network",
        adjacent: "Adjacent",
        adjacent_network: "Adjacent Network",
        local: "Local",
        physical: "Physical",
        required: "Required",
        unchanged: "Unchanged",
        changed: "Changed",

        not_defined: "Not Defined",
        none: "None",
        low: "Low",
        medium: "Medium",
        high: "High",
        critical: "Critical",

        unproven: "Unproven",
        proof_of_concept: "Proof-of-Concept",
        functional: "Functional",

        official_fix: "Official Fix",
        temporary_fix: "Temporary Fix",
        workaround: "Workaround",
        unavailable: "Unavailable",

        unknown: "Unknown",
        reasonable: "Reasonable",
        confirmed: "Confirmed",

        validator: "Invalid or Incomplete CVSS Vector String",
    },

    cvss_calculator_tooltip: {
        baseMetricGroup_Legend:
            "The Base Metric group represents the intrinsic  characteristics of a vulnerability that are constant over time and across user environments. Determine the vulnerable component and score Attack Vector, Attack Complexity, Privileges Required and User Interaction relative to this.",
        AV_Heading:
            "This metric reflects the context by which vulnerability exploitation is possible. The Base Score increases the more remote (logically, and physically) an attacker can be in order to exploit the vulnerable component.",
        AV_N_Label:
            "The vulnerable component is bound to the network stack and the set of possible attackers extends beyond the other options listed, up to and including the entire Internet. Such a vulnerability is often termed 'remotely exploitable' and can be thought of as an attack being exploitable at the protocol level one or more network hops away (e.g., across one or more routers).",
        AV_A_Label:
            "The vulnerable component is bound to the network stack, but the attack is limited at the protocol level to a logically adjacent topology. This can mean an attack must be launched from the same shared physical (e.g., Bluetooth or IEEE 802.11) or logical (e.g., local IP subnet) network, or from within a secure or otherwise limited administrative domain (e.g., MPLS, secure VPN to an administrative network zone).",
        AV_L_Label:
            "The vulnerable component is not bound to the network stack and the attacker’s path is via read/write/execute capabilities. Either: the attacker exploits the vulnerability by accessing the target system locally (e.g., keyboard, console), or remotely (e.g., SSH); or the attacker relies on User Interaction by another person to perform actions required to exploit the vulnerability (e.g., tricking a legitimate user into opening a malicious document).",
        AV_P_Label:
            "The attack requires the attacker to physically touch or manipulate the vulnerable component. Physical interaction may be brief or persistent.",
        AC_Heading:
            "This metric describes the conditions beyond the attacker’s control that must exist in order to exploit the vulnerability. Such conditions may require the collection of more information about the target or computational exceptions. The assessment of this metric excludes any requirements for user interaction in order to exploit the vulnerability. If a specific configuration is required for an attack to succeed, the Base metrics should be scored assuming the vulnerable component is in that configuration.",
        AC_L_Label:
            "Specialized access conditions or extenuating circumstances do not exist. An attacker can expect repeatable success against the vulnerable component.",
        AC_H_Label:
            "A successful attack depends on conditions beyond the attacker's control. That is, a successful attack cannot be accomplished at will, but requires the attacker to invest in some measurable amount of effort in preparation or execution against the vulnerable component before a successful attack can be expected. For example, a successful attack may require an attacker to: gather knowledge about the environment in which the vulnerable target/component exists; prepare the target environment to improve exploit reliability; or inject themselves into the logical network path between the target and the resource requested by the victim in order to read and/or modify network communications (e.g., a man in the middle attack).",
        PR_Heading:
            "This metric describes the level of privileges an attacker must possess before successfully exploiting the vulnerability.",
        PR_N_Label:
            "The attacker is unauthorized prior to attack, and therefore does not require any access to settings or files to carry out an attack.",
        PR_L_Label:
            "The attacker is authorized with (i.e., requires) privileges that provide basic user capabilities that could normally affect only settings and files owned by a user. Alternatively, an attacker with Low privileges may have the ability to cause an impact only to non-sensitive resources.",
        PR_H_Label:
            "The attacker is authorized with (i.e., requires) privileges that provide significant (e.g., administrative) control over the vulnerable component that could affect component-wide settings and files.",
        UI_Heading:
            "This metric captures the requirement for a user, other than the attacker, to participate in the successful compromise the vulnerable component. This metric determines whether the vulnerability can be exploited solely at the will of the attacker, or whether a separate user (or user-initiated process) must participate in some manner.",
        UI_N_Label:
            "The vulnerable system can be exploited without any interaction from any user.",
        UI_R_Label:
            "Successful exploitation of this vulnerability requires a user to take some action before the vulnerability can be exploited.",
        S_Heading:
            "Does a successful attack impact a component other than the vulnerable component? If so, the Base Score increases and the Confidentiality, Integrity and Authentication metrics should be scored relative to the impacted component.",
        S_U_Label:
            "An exploited vulnerability can only affect resources managed by the same security authority. In this case, the vulnerable component and the impacted component are either the same, or both are managed by the same security authority.",
        S_C_Label:
            "An exploited vulnerability can affect resources beyond the security scope managed by the security authority of the vulnerable component. In this case, the vulnerable component and the impacted component are different and managed by different security authorities.",
        C_Heading:
            "This metric measures the impact to the confidentiality of the information resources managed by a software component due to a successfully exploited vulnerability. Confidentiality refers to limiting information access and disclosure to only authorized users, as well as preventing access by, or disclosure to, unauthorized ones.",
        C_N_Label:
            "There is no loss of confidentiality within the impacted component.",
        C_L_Label:
            "There is some loss of confidentiality. Access to some restricted information is obtained, but the attacker does not have control over what information is obtained, or the amount or kind of loss is limited. The information disclosure does not cause a direct, serious loss to the impacted component.",
        C_H_Label:
            "There is total loss of confidentiality, resulting in all resources within the impacted component being divulged to the attacker. Alternatively, access to only some restricted information is obtained, but the disclosed information presents a direct, serious impact.",
        I_Heading:
            "This metric measures the impact to integrity of a successfully exploited vulnerability. Integrity refers to the trustworthiness and veracity of information.",
        I_N_Label: "There is no loss of integrity within the impacted component.",
        I_L_Label:
            "Modification of data is possible, but the attacker does not have control over the consequence of a modification, or the amount of modification is limited. The data modification does not have a direct, serious impact on the impacted component.",
        I_H_Label:
            "There is a total loss of integrity, or a complete loss of protection. For example, the attacker is able to modify any/all files protected by the impacted component. Alternatively, only some files can be modified, but malicious modification would present a direct, serious consequence to the impacted component.",
        A_Heading:
            "This metric measures the impact to the availability of the impacted component resulting from a successfully exploited vulnerability. It refers to the loss of availability of the impacted component itself, such as a networked service (e.g., web, database, email). Since availability refers to the accessibility of information resources, attacks that consume network bandwidth, processor cycles, or disk space all impact the availability of an impacted component.",
        A_N_Label:
            "There is no impact to availability within the impacted component.",
        A_L_Label:
            "Performance is reduced or there are interruptions in resource availability. Even if repeated exploitation of the vulnerability is possible, the attacker does not have the ability to completely deny service to legitimate users. The resources in the impacted component are either partially available all of the time, or fully available only some of the time, but overall there is no direct, serious consequence to the impacted component.",
        A_H_Label:
            "There is total loss of availability, resulting in the attacker being able to fully deny access to resources in the impacted component; this loss is either sustained (while the attacker continues to deliver the attack) or persistent (the condition persists even after the attack has completed). Alternatively, the attacker has the ability to deny some availability, but the loss of availability presents a direct, serious consequence to the impacted component (e.g., the attacker cannot disrupt existing connections, but can prevent new connections; the attacker can repeatedly exploit a vulnerability that, in each instance of a successful attack, leaks a only small amount of memory, but after repeated exploitation causes a service to become completely unavailable).",
        temporalMetricGroup_Legend:
            "The Temporal metrics measure the current state of exploit techniques or code availability, the existence of any patches or workarounds, or the confidence that one has in the description of a vulnerability.",
        E_Heading:
            "This metric measures the likelihood of the vulnerability being attacked, and is typically based on the current state of exploit techniques, exploit code availability, or active, 'in-the-wild' exploitation.",
        E_X_Label:
            "Assigning this value indicates there is insufficient information to choose one of the other values, and has no impact on the overall Temporal Score, i.e., it has the same effect on scoring as assigning High.",
        E_U_Label: "No exploit code is available, or an exploit is theoretical.",
        E_P_Label:
            "Proof-of-concept exploit code is available, or an attack demonstration is not practical for most systems. The code or technique is not functional in all situations and may require substantial modification by a skilled attacker.",
        E_F_Label:
            "Functional exploit code is available. The code works in most situations where the vulnerability exists.",
        E_H_Label:
            "Functional autonomous code exists, or no exploit is required (manual trigger) and details are widely available. Exploit code works in every situation, or is actively being delivered via an autonomous agent (such as a worm or virus). Network-connected systems are likely to encounter scanning or exploitation attempts. Exploit development has reached the level of reliable, widely-available, easy-to-use automated tools.",
        RL_Heading:
            "The Remediation Level of a vulnerability is an important factor for prioritization. The typical vulnerability is unpatched when initially published. Workarounds or hotfixes may offer interim remediation until an official patch or upgrade is issued. Each of these respective stages adjusts the temporal score downwards, reflecting the decreasing urgency as remediation becomes final.",
        RL_X_Label:
            "Assigning this value indicates there is insufficient information to choose one of the other values, and has no impact on the overall Temporal Score, i.e., it has the same effect on scoring as assigning Unavailable.",
        RL_O_Label:
            "A complete vendor solution is available. Either the vendor has issued an official patch, or an upgrade is available.",
        RL_T_Label:
            "There is an official but temporary fix available. This includes instances where the vendor issues a temporary hotfix, tool, or workaround.",
        RL_W_Label:
            "There is an unofficial, non-vendor solution available. In some cases, users of the affected technology will create a patch of their own or provide steps to work around or otherwise mitigate the vulnerability.",
        RL_U_Label:
            "There is either no solution available or it is impossible to apply.",
        RC_Heading:
            "This metric measures the degree of confidence in the existence of the vulnerability and the credibility of the known technical details. Sometimes only the existence of vulnerabilities are publicized, but without specific details. For example, an impact may be recognized as undesirable, but the root cause may not be known. The vulnerability may later be corroborated by research which suggests where the vulnerability may lie, though the research may not be certain. Finally, a vulnerability may be confirmed through acknowledgement by the author or vendor of the affected technology. The urgency of a vulnerability is higher when a vulnerability is known to exist with certainty. This metric also suggests the level of technical knowledge available to would-be attackers.",
        RC_X_Label:
            "Assigning this value indicates there is insufficient information to choose one of the other values, and has no impact on the overall Temporal Score, i.e., it has the same effect on scoring as assigning Confirmed.",
        RC_U_Label:
            "There are reports of impacts that indicate a vulnerability is present. The reports indicate that the cause of the vulnerability is unknown, or reports may differ on the cause or impacts of the vulnerability. Reporters are uncertain of the true nature of the vulnerability, and there is little confidence in the validity of the reports or whether a static Base score can be applied given the differences described. An example is a bug report which notes that an intermittent but non-reproducible crash occurs, with evidence of memory corruption suggesting that denial of service, or possible more serious impacts, may result.",
        RC_R_Label:
            "Significant details are published, but researchers either do not have full confidence in the root cause, or do not have access to source code to fully confirm all of the interactions that may lead to the result. Reasonable confidence exists, however, that the bug is reproducible and at least one impact is able to be verified (Proof-of-concept exploits may provide this). An example is a detailed write-up of research into a vulnerability with an explanation (possibly obfuscated or 'left as an exercise to the reader') that gives assurances on how to reproduce the results.",
        RC_C_Label:
            "Detailed reports exist, or functional reproduction is possible (functional exploits may provide this). Source code is available to independently verify the assertions of the research, or the author or vendor of the affected code has confirmed the presence of the vulnerability.",
        environmentalMetricGroup_Legend:
            "These metrics enable the analyst to customize the CVSS score depending on the importance of the affected IT asset to a user’s organization, measured in terms of complementary/alternative security controls in place, Confidentiality, Integrity, and Availability. The metrics are the modified equivalent of base metrics and are assigned metric values based on the component placement in organization infrastructure.",
        CR_Heading:
            "These metrics enable the analyst to customize the CVSS score depending on the importance of the Confidentiality of the affected IT asset to a user’s organization, relative to other impacts. This metric modifies the environmental score by reweighting the Modified Confidentiality impact metric versus the other modified impacts.",
        CR_X_Label:
            "Assigning this value indicates there is insufficient information to choose one of the other values, and has no impact on the overall Environmental Score, i.e., it has the same effect on scoring as assigning Medium.",
        CR_L_Label:
            "Loss of Confidentiality is likely to have only a limited adverse effect on the organization or individuals associated with the organization (e.g., employees, customers).",
        CR_M_Label:
            "Assigning this value to the metric will not influence the score.",
        CR_H_Label:
            "Loss of Confidentiality is likely to have a catastrophic adverse effect on the organization or individuals associated with the organization (e.g., employees, customers).",
        IR_Heading:
            "These metrics enable the analyst to customize the CVSS score depending on the importance of the Integrity of the affected IT asset to a user’s organization, relative to other impacts. This metric modifies the environmental score by reweighting the Modified Integrity impact metric versus the other modified impacts.",
        IR_X_Label:
            "Assigning this value indicates there is insufficient information to choose one of the other values, and has no impact on the overall Environmental Score, i.e., it has the same effect on scoring as assigning Medium.",
        IR_L_Label:
            "Loss of Integrity is likely to have only a limited adverse effect on the organization or individuals associated with the organization (e.g., employees, customers).",
        IR_M_Label:
            "Assigning this value to the metric will not influence the score.",
        IR_H_Label:
            "Loss of Integrity is likely to have a catastrophic adverse effect on the organization or individuals associated with the organization (e.g., employees, customers).",
        AR_Heading:
            "These metrics enable the analyst to customize the CVSS score depending on the importance of the Availability of the affected IT asset to a user’s organization, relative to other impacts. This metric modifies the environmental score by reweighting the Modified Availability impact metric versus the other modified impacts.",
        AR_X_Label:
            "Assigning this value indicates there is insufficient information to choose one of the other values, and has no impact on the overall Environmental Score, i.e., it has the same effect on scoring as assigning Medium.",
        AR_L_Label:
            "Loss of Availability is likely to have only a limited adverse effect on the organization or individuals associated with the organization (e.g., employees, customers).",
        AR_M_Label:
            "Assigning this value to the metric will not influence the score.",
        AR_H_Label:
            "Loss of Availability is likely to have a catastrophic adverse effect on the organization or individuals associated with the organization (e.g., employees, customers).",
        MAV_Heading:
            "This metric reflects the context by which vulnerability exploitation is possible. The Environmental Score increases the more remote (logically, and physically) an attacker can be in order to exploit the vulnerable component.",
        MAV_X_Label: "The value assigned to the corresponding Base metric is used.",
        MAV_N_Label:
            "The vulnerable component is bound to the network stack and the set of possible attackers extends beyond the other options listed, up to and including the entire Internet. Such a vulnerability is often termed 'remotely exploitable' and can be thought of as an attack being exploitable at the protocol level one or more network hops away.",
        MAV_A_Label:
            "The vulnerable component is bound to the network stack, but the attack is limited at the protocol level to a logically adjacent topology. This can mean an attack must be launched from the same shared physical (e.g., Bluetooth or IEEE 802.11) or logical (e.g., local IP subnet) network, or from within a secure or otherwise limited administrative domain (e.g., MPLS, secure VPN).",
        MAV_L_Label:
            "The vulnerable component is not bound to the network stack and the attacker’s path is via read/write/execute capabilities. Either: the attacker exploits the vulnerability by accessing the target system locally (e.g., keyboard, console), or remotely (e.g., SSH); or the attacker relies on User Interaction by another person to perform actions required to exploit the vulnerability (e.g., tricking a legitimate user into opening a malicious document).",
        MAV_P_Label:
            "The attack requires the attacker to physically touch or manipulate the vulnerable component. Physical interaction may be brief or persistent.",
        MAC_Heading:
            "This metric describes the conditions beyond the attacker’s control that must exist in order to exploit the vulnerability. Such conditions may require the collection of more information about the target or computational exceptions. The assessment of this metric excludes any requirements for user interaction in order to exploit the vulnerability. If a specific configuration is required for an attack to succeed, the Base metrics should be scored assuming the vulnerable component is in that configuration.",
        MAC_X_Label: "The value assigned to the corresponding Base metric is used.",
        MAC_L_Label:
            "Specialized access conditions or extenuating circumstances do not exist. An attacker can expect repeatable success against the vulnerable component.",
        MAC_H_Label:
            "A successful attack depends on conditions beyond the attacker's control. That is, a successful attack cannot be accomplished at will, but requires the attacker to invest in some measurable amount of effort in preparation or execution against the vulnerable component before a successful attack can be expected. For example, a successful attack may require an attacker to: gather knowledge about the environment in which the vulnerable target/component exists; prepare the target environment to improve exploit reliability; or inject themselves into the logical network path between the target and the resource requested by the victim in order to read and/or modify network communications (e.g., a man in the middle attack).",
        MPR_Heading:
            "This metric describes the level of privileges an attacker must possess before successfully exploiting the vulnerability.",
        MPR_X_Label: "The value assigned to the corresponding Base metric is used.",
        MPR_N_Label:
            "The attacker is unauthorized prior to attack, and therefore does not require any access to settings or files to carry out an attack.",
        MPR_L_Label:
            "The attacker is authorized with (i.e., requires) privileges that provide basic user capabilities that could normally affect only settings and files owned by a user. Alternatively, an attacker with Low privileges may have the ability to cause an impact only to non-sensitive resources.",
        MPR_H_Label:
            "The attacker is authorized with (i.e., requires) privileges that provide significant (e.g., administrative) control over the vulnerable component that could affect component-wide settings and files.",
        MUI_Heading:
            "This metric captures the requirement for a user, other than the attacker, to participate in the successful compromise the vulnerable component. This metric determines whether the vulnerability can be exploited solely at the will of the attacker, or whether a separate user (or user-initiated process) must participate in some manner.",
        MUI_X_Label: "The value assigned to the corresponding Base metric is used.",
        MUI_N_Label:
            "The vulnerable system can be exploited without any interaction from any user.",
        MUI_R_Label:
            "Successful exploitation of this vulnerability requires a user to take some action before the vulnerability can be exploited.",
        MS_Heading:
            "Does a successful attack impact a component other than the vulnerable component? If so, the Base Score increases and the Confidentiality, Integrity and Authentication metrics should be scored relative to the impacted component.",
        MS_X_Label: "The value assigned to the corresponding Base metric is used.",
        MS_U_Label:
            "An exploited vulnerability can only affect resources managed by the same security authority. In this case, the vulnerable component and the impacted component are either the same, or both are managed by the same security authority.",
        MS_C_Label:
            "An exploited vulnerability can affect resources beyond the security scope managed by the security authority of the vulnerable component. In this case, the vulnerable component and the impacted component are different and managed by different security authorities.",
        MC_Heading:
            "This metric measures the impact to the confidentiality of the information resources managed by a software component due to a successfully exploited vulnerability. Confidentiality refers to limiting information access and disclosure to only authorized users, as well as preventing access by, or disclosure to, unauthorized ones.",
        MC_X_Label: "The value assigned to the corresponding Base metric is used.",
        MC_N_Label:
            "There is no loss of confidentiality within the impacted component.",
        MC_L_Label:
            "There is some loss of confidentiality. Access to some restricted information is obtained, but the attacker does not have control over what information is obtained, or the amount or kind of loss is limited. The information disclosure does not cause a direct, serious loss to the impacted component.",
        MC_H_Label:
            "There is total loss of confidentiality, resulting in all resources within the impacted component being divulged to the attacker. Alternatively, access to only some restricted information is obtained, but the disclosed information presents a direct, serious impact.",
        MI_Heading:
            "This metric measures the impact to integrity of a successfully exploited vulnerability. Integrity refers to the trustworthiness and veracity of information.",
        MI_X_Label: "The value assigned to the corresponding Base metric is used.",
        MI_N_Label: "There is no loss of integrity within the impacted component.",
        MI_L_Label:
            "Modification of data is possible, but the attacker does not have control over the consequence of a modification, or the amount of modification is limited. The data modification does not have a direct, serious impact on the impacted component.",
        MI_H_Label:
            "There is a total loss of integrity, or a complete loss of protection. For example, the attacker is able to modify any/all files protected by the impacted component. Alternatively, only some files can be modified, but malicious modification would present a direct, serious consequence to the impacted component.",
        MA_Heading:
            "This metric measures the impact to the availability of the impacted component resulting from a successfully exploited vulnerability. It refers to the loss of availability of the impacted component itself, such as a networked service (e.g., web, database, email). Since availability refers to the accessibility of information resources, attacks that consume network bandwidth, processor cycles, or disk space all impact the availability of an impacted component.",
        MA_X_Label: "The value assigned to the corresponding Base metric is used.",
        MA_N_Label:
            "There is no impact to availability within the impacted component.",
        MA_L_Label:
            "Performance is reduced or there are interruptions in resource availability. Even if repeated exploitation of the vulnerability is possible, the attacker does not have the ability to completely deny service to legitimate users. The resources in the impacted component are either partially available all of the time, or fully available only some of the time, but overall there is no direct, serious consequence to the impacted component.",
        MA_H_Label:
            "There is total loss of availability, resulting in the attacker being able to fully deny access to resources in the impacted component; this loss is either sustained (while the attacker continues to deliver the attack) or persistent (the condition persists even after the attack has completed). Alternatively, the attacker has the ability to deny some availability, but the loss of availability presents a direct, serious consequence to the impacted component (e.g., the attacker cannot disrupt existing connections, but can prevent new connections; the attacker can repeatedly exploit a vulnerability that, in each instance of a successful attack, leaks a only small amount of memory, but after repeated exploitation causes a service to become completely unavailable).",
    },

    report_type: {
        add_new: "Pridať nový typ analýzy",
        edit: "Upraviť typ analýzy",
        error: "Nepodarilo sa uložiť typ analýzy",
        name: "Názov",
        description: "Popis",
        section_title: "Názov sekcie",
        new_group: "Nová skupina atribútov",
        successful: "Nový typ analýzy bol úspešne pridaný",
        successful_edit: "Typ analýzy bol úspešne aktualizovaný",
        removed_error: "Typ analýzy sa používa a nie je možné ho odstrániť",
        removed: "Typ analýzy bol úspešne odstránený",
        total_count: "Počet typov analýz: ",
    },

    report_item: {
        add_new: "Nová analýza",
        edit: "Upraviť analýzu",
        read: "Náhľad analýzy",
        error: "Nepodarilo sa vytvoriť analýzu",
        title: "Názov",
        title_prefix: "Prefix názvu",
        report_type: "Typ analýzy",
        state: "Stav",
        successful: "Nová analýza bola úspešne pridaná",
        successful_edit: "Analýza bola úspešne uložená",
        removed: "Analýza bola úspešne odstránená",
        removed_error: "Analýza sa používa a nie je možné ju odstrániť",
        removed_from_report: "Novinka bola úspešne odstránená z analýzy",
        select: "Vybrať analýzu",
        select_remote: "Vybrať analýzu zo vzdialených inštancií",
        attributes: "Atribúty",
        side_by_side: "Zobraziť vedľa seba",
        confirm_close: {
            message:
                "Máte neuložené zmeny. Naozaj chcete zatvoriť túto analýzu?",
        },
        tooltip: {
            sort_time: "Zoradiť hodnoty od najnovších",
            sort_user: "Zobraziť najprv moje hodnoty, potom ostatné",
            cvss_detail: "Zobraziť definíciu kalkulačky CVSS",
            enum_selector: "Zobraziť okno na vyhľadávanie hodnôt",
            delete_value: "Odstrániť hodnotu z tohto atribútu",
            add_value: "Pridať novú hodnotu k tomuto atribútu",
            auto_generate: "Automaticky vygenerovať",
        },
    },

    product: {
        add_new: "Pridať novú publikáciu",
        edit: "Editovať publikáciu",
        error: "Nemôžem vytvoriť túto publikáciu",
        title: "Meno",
        name: "Názov",
        description: "Popis",
        report_type: "Typ publikácie",
        state: "Stav",
        successful: "Nová publikácia bola úspešne vytvorená",
        successful_edit: "Publikácia bola úspešne uložená",
        removed: "Publikácia bola úspešne zmazaná",
        removed_error: "Publikácia sa používa a nemôže byť zmazaná",
        preview: "Náhľad",
        publish: "Zverejniť",
        publish_confirmation: "Ste si istý, že chcete zverejniť túto publikáciu?",
        publish_successful: "Publikácia bola úspešne zverejnená",
        publish_failed: "Nepodarilo sa zverejniť publikáciu",
        publish_error: "Pri zverejňovaní nastala chyba",
        no_publisher_selected: "Vyberte aspoň jedného vydavateľa",
        total_count: "Počet publikácií: ",
        confirm_close: {
            message: "Máte neuložené zmeny. Naozaj chcete zavrieť túto publikáciu bez uloženia zmien?",
        },
        publish_unsaved: {
            title: "Zverejniť neuloženú publikáciu",
            message: "Táto publikácia má neuložené zmeny. Ako chcete pokračovať?",
            close: "Zavrieť",
            save_and_publish: "Uložiť a zverejniť",
            publish_only: "Zverejniť bez uloženia",
        },
    },

    analyze: {
        sort: "Zoradiť podľa",
        from: "Od",
        to: "Do",
        total_count: "Počet analýz: ",
        select_all_success: "{count} položiek vybraných",
        tooltip: {
            filter_all: "Aktuálne zobrazené: všetko",
            filter_completed: "Aktuálne zobrazené: hotové",
            filter_incomplete: "Aktuálne zobrazené: nedokončené",
            range: {
                ALL: "Zobraziť všetky analýzy",
                TODAY: "Zobraziť dnešné analýzy",
                WEEK: "Zobraziť analýzy za posledný týždeň",
                MONTH: "Zobraziť analýzy za posledný mesiac",
                LAST_7_DAYS: "Zobraziť analýzy za posledných 7 dní",
                LAST_31_DAYS: "Zobraziť analýzy za posledných 31 dní",
            },
            sort: {
                time: {
                    ascending: "Zoradiť podľa dátumu vytvorenia vzostupne",
                    descending: "Zoradiť podľa dátumu vytvorenia zostupne",
                },
            },
            toggle_selection: "Režim výberu analýz",
            select_all: "Vybrať všetko",
            unselect_all: "Zrušiť výber",
            delete_items: "Zmazať analýzy",
            publish_items: "Vytvoriť z analýzy publikáciu",
            delete_item: "Zmazať analýzu",
            remove_item: "Odstrániť analýzu",
            publish_item: "Vytvoriť publikáciu z analýzy",
        },
    },

    assess: {
        source: "Zdroj",
        comments: "Komentáre",
        collected: "Získané",
        published: "Publikované",
        author: "Autor",
        add_news_item: "Pridať novinku",
        select_news_item: "Vybrať novinku",
        aggregate_detail: "Detail zlúčenej novinky",
        aggregate_info: "Info",
        aggregate_title: "Názov",
        aggregate_description: "Popis",
        attributes: "Atributy",
        title: "Názov",
        description: "Popis",
        download: "Stiahnuť",
        total_count: "Počet noviniek: ",
        selected_count: "Počet vybraných noviniek: ",
        select_all_success: "{count} položiek vybraných",
        tooltip: {
            filter_all: "Aktuálne zobrazené: všetko",
            filter_read: "Aktuálne zobrazené: prečítané",
            filter_unread: "Aktuálne zobrazené: neprečítané",
            filter_important: "Aktuálne zobrazené: dôležité",
            filter_unimportant: "Aktuálne zobrazené: nedôležité",
            filter_relevant: "Aktuálne zobrazené: relevantné",
            filter_irrelevant: "Aktuálne zobrazené: nerelevantné",
            range: {
                ALL: "Zobraziť všetky novinky",
                TODAY: "Zobraziť dnešné novinky",
                WEEK: "Zobraziť novinky za minulý týždeň",
                MONTH: "Zobraziť novinky za minulý mesiac",
                LAST_7_DAYS: "Zobraziť novinky za posledných 7 dní",
                LAST_31_DAYS: "Zobraziť novinky za posledných 31 dní",
            },
            sort: {
                date: {
                    ascending: "Zoradiť podľa dátumu zberu vzostupne",
                    descending: "Zoradiť podľa dátumu zberu zostupne",
                },
                relevance: {
                    ascending: "Zoradiť podľa relevancie vzostupne",
                    descending: "Zoradiť podľa relevancie zostupne",
                },
            },
            hide_review: 'Skryť náhľady noviniek',
            hide_source_link: 'Skryť odkazy na zdroje v novinkách',
            highlight_wordlist: "Zvýrazniť slová zo zoznamov slov",
            toggle_selection: "Režim výberu noviniek",
            select_all: "Vybrať všetko",
            unselect_all: "Zrušiť výber",
            group_items: "Zoskupiť novinky",
            ungroup_items: "Zrušiť zoskupenie noviniek",
            analyze_items: "Vytvoriť z noviniek analýzu",
            read_items: "Označiť novinky ako prečítané",
            important_items: "Označiť novinky ako dôležité",
            like_items: "Páči sa mi",
            dislike_items: "Nepáči sa mi",
            delete_items: "Odstrániť novinky",
            open_source: "Otvoriť zdroj novinky v novej karte",
            ungroup_item: "Oddeliť novinku zo skupiny",
            analyze_item: "Vytvoriť z novinky analýzu",
            read_item: "Označiť ako prečítané",
            important_item: "Označiť ako dôležité",
            like_item: "Páči sa mi",
            dislike_item: "Nepáči sa mi",
            delete_item: "Odstrániť novinku",
            remove_item: "Odstrániť novinku",
            show_reports: "Zobraziť analýzy obsahujúce túto položku",
        },
        shortcuts: {
            enter_filter_mode:
                "Zapnúť mód klávesových skratiek 'filter'. Ukončite klávesou Escape.",
            enter_view_mode: "Zapnúť mód klávesových skratiek 'náhľad'. Ukončite klávesou Escape.",
            default_mode: "Mód klávesových skratiek 'predvolený'.",
            aggregate_no_group:
                "Nie je možné otvoriť neagregovanú novinku, funguje len so skupinou noviniek.",
        },
        reports_dialog: {
            title: "Analýzy obsahujúce túto položku",
            no_reports: "Táto položka nie je v žiadnych analýzach",
            error_loading: "Chyba pri načítavaní analýz",
        },
    },

    assets: {
        tooltip: {
            filter_vulnerable: "Zobraziť/skryť zraniteľné aktíva",
            sort: {
                vulnerability: {
                    descending: "Zoradiť podľa zraniteľnosti zostupne",
                },
                alphabetical: {
                    ascending: "Zoradiť abecedne vzostupne",
                },
            },
        },
    },

    publish: {
        tooltip: {
            filter_all: "Aktuálne zobrazené: všetky",
            filter_published: "Aktuálne zobrazené: publikované",
            filter_unpublished: "Aktuálne zobrazené: nepublikované",
            range: {
                ALL: "Zobraziť všetky publikácie",
                TODAY: "Zobraziť dnešné publikácie",
                WEEK: "Zobraziť publikácie za posledný týždeň",
                MONTH: "Zobraziť publikácie za posledný mesiac",
                LAST_7_DAYS: "Zobraziť publikácie za posledných 7 dní",
                LAST_31_DAYS: "Zobraziť publikácie za posledných 31 dní",
            },
            sort: {
                date: {
                    ascending: "Zoradiť podľa dátumu vytvorenia vzostupne",
                    descending: "Zoradiť podľa dátumu vytvorenia zostupne",
                },
            },
            delete_item: "Odstrániť publikáciu",
        },
    },

    toolbar_filter: {
        search: "Hľadanie",
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
        read_item: "Označiť ako prečítané",
        important_item: "Označiť ako dôležité",
        like_item: "Označiť ako To sa mi páči",
        unlike_item: "Označiť ako To sa mi nepáči",
        delete_item: "Zmazať",
        press_key: "Stlačte klávesu pre ",
        selection: "Výber",
        group: "Zoskupiť",
        ungroup: "Zrušiť zoskupenie",
        new_product: "Nová publikácia",
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
        open_item_source: "Otvoriť zdroj položky",
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
        CASCADE_STATES_ENABLED: "Automatické kaskádové zmeny stavov",
        DARK_THEME: "Tmavý motiv",
        DATE_FORMAT: 'Formát dátumu',
        HOTKEYS: "Povoliť klávesové skratky",
        UI_LANGUAGE: "Jazyk používateľského rozhrania",
        CONTENT_DEFAULT_LANGUAGE: "Predvolený jazyk pre analýzy/publikácie",
        REPORT_SELECTOR_READ_ONLY: 'Otvoriť výber analýz v režime iba na čítanie',
        SPELLCHECK: "Kontrolovať pravopis",
        TAG_COLOR: "Farebný oblak značiek",
        TIME_FORMAT: 'Formát času',
    },

    word_list: {
        add_new: "Pridať nový slovník",
        add_word: "Pridať slovo",
        edit_word: "Upraviť slovo",
        edit: "Upraviť slovník",
        error: "Nepodarilo sa uložiť slovník",
        name: "Názov",
        description: "Popis",
        link: "URL",
        use_for_stop_words: "Použiť ako zoznam stopslov",
        successful: "Nový slovník bol úspešne pridaný",
        successful_edit: "Slovník bol úspešne aktualizovaný",
        remove: "Slovník bol úspešne odstránený",
        removed_error: "Slovník sa používa a nie je možné ho odstrániť",
        value: "Hodnota",
        new_word: "Nové slovo",
        words: "Slová",
        new_category: "Nová kategória",
        total_count: "Počet slovníkov: ",
        file_has_header: "Súbor obsahuje hlavičku",
        import_from_csv: "Import z CSV",
        load_csv_file: "Načítať CSV súbor",
        download_from_link: "Stiahnuť z URL",
        import: "Import",
        close: "Zavrieť",
        delete_existing_words: "Odstrániť existujúce slová",
        delete_category: "Odstrániť kategóriu",
    },

    workflow: {
        states_tab: "Stavy",
        state_workflow_tab: "Workflow stavov",
        tags_tab: "Tagy",
        tag_workflow_tab: "Workflow tagov",
        states: {
            tab_description: "Tu môžete spravovať stavy používané vo workflow.",
            display_name: "Zobrazovaný názov",
            description: "Popis",
            add_new: "Pridať nový stav",
            edit: "Upraviť stav",
            color: "Farba",
            icon: "Ikona",
            type: "Typ",
            error: "Nepodarilo sa uložiť stav",
            no_state: "Bez stavu",
            published: "Publikované",
            work_in_progress: "Rozpracované",
            completed: "Dokončené",
            successful: "Nový stav bol úspešne pridaný",
            successful_edit: "Stav bol úspešne aktualizovaný",
            cannot_edit_system_state: "Systémový stav nie je možné upraviť",
            cannot_delete_system_state: "Systémový stav nie je možné odstrániť",
            remove: "Stav bol úspešne odstránený",
            removed_error: "Stav sa používa a nie je možné ho odstrániť",
        },
        state_workflow: {
            tab_description: "Tu môžete spravovať priradenie stavov k entitám.",
            state: "Stav",
            state_type: "Typ stavu",
            entity_type: "Typ entity",
            is_active: "Aktívny",
            sort_order: "Poradie",
            add_state_association: "Pridať priradenie stavu",
            edit_state_association: "Upraviť priradenie stavu",
            filter_by_entity_type: "Filtrovať podľa typu entity",
            all_entity_types: "Všetky typy entít",
            association_already_exists: "Toto priradenie stavu už existuje",
            successful: "Nové priradenie bolo úspešne pridané",
            successful_edit: "Priradenie bolo úspešne aktualizované",
            cannot_edit_system_association: "Systémové priradenie nie je možné upraviť",
            cannot_delete_system_association: "Systémové priradenie nie je možné odstrániť",
            error: "Nepodarilo sa uložiť priradenie",
            remove: "Priradenie stavu bolo úspešne odstránené",
            removed_error: "Priradenie stavu sa používa a nie je možné ho odstrániť",
            state_required: "Stav je povinný",
            entity_type_required: "Typ entity je povinný",
        },
        entity_types: {
            report_item: "Analýza",
            product: "Publikácia",
        },
        state_types: {
            normal: "Normálny",
            initial: "Počiatočný",
            final: "Koncový",
        },
    },

    ai_provider: {
        name: "Názov",
        api_type: "Typ API",
        api_url: "API URL",
        model: "Model",
        add_new: "Pridať nový AI model",
        edit: "Upraviť AI model",
        successful: "Nový AI model bol úspešne pridaný",
        successful_edit: "AI model bol úspešne aktualizovaný",
        error: "Nepodarilo sa uložiť AI model",
        remove: "AI model bol úspešne odstránený",
        removed_error: "AI model sa používa a nie je možné ho odstrániť",
    },

    data_provider: {
        name: "Názov",
        api_type: "Typ API",
        api_url: "API URL",
        user_agent: "User-Agent",
        web_url: "Web URL",
        add_new: "Pridať nový zdroj dát",
        edit: "Upraviť zdroj dát",
        successful: "Nový zdroj dát bol úspešne pridaný",
        successful_edit: "Zdroj dát bol úspešne aktualizovaný",
        error: "Nepodarilo sa uložiť zdroj dát",
        remove: "Zdroj dát bol úspešne odstránený",
        removed_error: "Zdroj dát sa používa a nie je možné ho odstrániť",
        total_count: "Počet zdrojov dát: ",
    },

    asset_group: {
        add_new: "Pridať novú skupinu aktív",
        edit: "Upraviť skupinu aktív",
        error: "Nepodarilo sa uložiť skupinu aktív",
        name: "Názov",
        description: "Popis",
        notification_templates: "Šablóny notifikácií",
        allowed_users: "Povolení používatelia (ak nie je vybraný žiadny, povolení sú všetci)",
        successful: "Nová skupina aktív bola úspešne pridaná",
        successful_edit: "Skupina aktív bola úspešne aktualizovaná",
        removed: "Skupina aktív bola úspešne odstránená",
        removed_error: "Skupina aktív sa používa a nie je možné ju odstrániť",
        total_count: "Počet skupín aktív: ",
    },

    notification_template: {
        add_new: "Pridať novú šablónu notifikácie",
        add_recipient: "Pridať príjemcu",
        edit_recipient: "Upraviť príjemcu",
        edit: "Upraviť šablónu notifikácie",
        error: "Nepodarilo sa uložiť šablónu notifikácie",
        name: "Názov",
        description: "Popis",
        message_title: "Názov správy",
        message_body: "Text správy",
        new_recipient: "Nový príjemca",
        recipient_name: "Meno príjemcu",
        email: "Email",
        recipients: "Príjemcovia",
        successful: "Nová šablóna notifikácie bola úspešne pridaná",
        successful_edit: "Šablóna notifikácie bola úspešne aktualizovaná",
        removed: "Šablóna notifikácie bola úspešne odstránená",
        removed_error: "Šablóna notifikácie sa používa a nie je možné ju odstrániť",
        total_count: "Počet šablón notifikácií: ",
    },

    asset: {
        add_new: "Pridať nové aktívum",
        add_group_info: "Prosím, pridajte skupinu aktív",
        edit: "Upraviť aktívum",
        error: "Nepodarilo sa uložiť aktívum",
        name: "Názov",
        serial: "Sériové číslo",
        description: "Popis",
        cpe: "CPE kód",
        new_cpe: "Pridať CPE kód",
        cpes: "CPE kódy",
        value: "Hodnota",
        successful: "Nové aktívum bolo úspešne pridané",
        successful_edit: "Aktívum bolo úspešne aktualizované",
        removed: "Aktívum bolo úspešne odstránené",
        removed_error: "Aktívum sa používa a nie je možné ho odstrániť",
        total_count: "Počet aktív: ",
        vulnerabilities: "Zraniteľnosti",
        vulnerabilities_count: "Zraniteľnosti: ",
        no_vulnerabilities: "Žiadne zraniteľnosti",
        import_csv: "Import CSV",
        import_from_csv: "Import CPE z CSV",
        file_has_header: "Súbor obsahuje hlavičku",
        load_csv_file: "Načítať CSV súbor",
        import: "Import",
        close: "Zavrieť",
    },

    remote_access: {
        add_new: "Pridať nový vzdialený prístup",
        edit: "Upraviť vzdialený prístup",
        error: "Nepodarilo sa uložiť vzdialený prístup",
        name: "Názov",
        description: "Popis",
        enabled: "Povolené",
        successful: "Nový vzdialený prístup bol úspešne pridaný",
        successful_edit: "Vzdialený prístup bol úspešne aktualizovaný",
        removed: "Vzdialený prístup bol úspešne odstránený",
        removed_error: "Vzdialený prístup sa používa a nie je možné ho odstrániť",
        osint_sources: "OSINT zdroje na zdieľanie",
        report_item_types: "Typy položiek analýzy na zdieľanie",
        total_count: "Počet vzdialených prístupov: ",
    },

    remote_node: {
        add_new: "Pridať novú vzdialenú inštanciu",
        edit: "Upraviť vzdialenú inštanciu",
        error: "Nepodarilo sa uložiť vzdialenú inštanciu",
        name: "Názov",
        description: "Popis",
        remote_url: "URL vzdialenej inštancie",
        event_url: "URL zdroja udalostí",
        enabled: "Povolené",
        connect: "Pripojiť sa k vzdialenej inštancii",
        connect_error: "Pripojenie zlyhalo. Nesprávny prístupový kľúč alebo inštancia nebeží.",
        connect_info: "Pripojenie k vzdialenej inštancii bolo úspešné.",
        sync_news_items: "Synchronizovať novinky",
        sync_report_items: "Synchronizovať položky analýz",
        osint_source_group: "Synchronizovať do skupiny OSINT zdrojov",
        successful: "Nová vzdialená inštancia bola úspešne pridaná",
        successful_edit: "Vzdialená inštancia bola úspešne aktualizovaná",
        removed: "Vzdialená inštancia bola úspešne odstránená",
        removed_error: "Vzdialená inštancia sa používa a nie je možné ju odstrániť",
        total_count: "Počet vzdialených inštancií: ",
    },

    drop_zone: {
        default_message: "Presuňte súbory sem alebo kliknite pre výber",
        file_description: "Popis",
        last_updated: "Naposledy aktualizované",
        download: "Stiahnuť",
        attachment_load: "Načítať prílohu",
        attachment_detail: "Detail prílohy",
    },

    error: {
        aggregate_in_use: "Niektoré vybrané novinky alebo zlúčené novinky sú už pripojené k analýze",
        server_error: "Neznámá chyba serveru...",
        validation: "Prosím vyplnte všetky povinné polia",
        select_all_failed: "Zlyhalo vybratie všetkých položiek",
    },

    confirm_close: {
        title: "Neuložené zmeny",
        continue: "Pokračovať v úpravách",
        save_and_close: "Uložiť a zavrieť",
        close: "Zavrieť bez uloženia",
    },

    common: {
        add: "Pridať",
        add_btn: "Pridať",
        save: "Uložiť",
        edit: "Upraviť",
        up: "Presunúť vyššie",
        down: "Presunúť nižšie",
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
