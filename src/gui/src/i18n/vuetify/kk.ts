import type { en } from 'vuetify/locale'

/**
 * Kazakh labels for Vuetify's own components (tables, pagination, pickers...), which Vuetify
 * does not ship. Typed against its English catalog, so a Vuetify upgrade that adds a label
 * fails the type check here instead of showing English in a Kazakh interface.
 */
const kk: typeof en = {
    badge: 'Белгі',
    open: 'Ашу',
    close: 'Жабу',
    dismiss: 'Жасыру',
    confirmEdit: {
        ok: 'OK',
        cancel: 'Бас тарту'
    },
    dataIterator: {
        noResultsText: 'Сәйкес жазбалар табылмады',
        loadingText: 'Элементтер жүктелуде...'
    },
    dataTable: {
        itemsPerPageText: 'Беттегі жолдар:',
        ariaLabel: {
            sortDescending: 'Кему ретімен сұрыпталған.',
            sortAscending: 'Өсу ретімен сұрыпталған.',
            sortNone: 'Сұрыпталмаған.',
            activateNone: 'Сұрыптауды алып тастау үшін белсендіріңіз.',
            activateDescending: 'Кему ретімен сұрыптау үшін белсендіріңіз.',
            activateAscending: 'Өсу ретімен сұрыптау үшін белсендіріңіз.',
            selectRow: 'Жолды таңдау',
            selectAll: 'Барлығын таңдау',
            selectGroup: 'Топты таңдау'
        },
        sortBy: 'Сұрыптау'
    },
    dataFooter: {
        itemsPerPageText: 'Беттегі элементтер:',
        itemsPerPageAll: 'Бәрі',
        nextPage: 'Келесі бет',
        prevPage: 'Алдыңғы бет',
        firstPage: 'Бірінші бет',
        lastPage: 'Соңғы бет',
        pageText: '{0}-{1} / {2}'
    },
    dateRangeInput: {
        divider: 'дейін'
    },
    monthPicker: {
        title: 'Айды таңдау',
        itemsSelected: '{0} таңдалды',
        header: 'Айды енгізу',
        range: {
            title: 'Айларды енгізу'
        },
        ariaLabel: {
            previousYear: 'Алдыңғы жыл',
            nextYear: 'Келесі жыл',
            selectYear: 'Жылды таңдау',
            currentMonth: 'Ағымдағы ай, {0}'
        }
    },
    datePicker: {
        itemsSelected: '{0} таңдалды',
        range: {
            title: 'Күндерді таңдау',
            header: 'Күндерді енгізу'
        },
        title: 'Күнді таңдау',
        header: 'Күнді енгізу',
        input: {
            placeholder: 'Күнді енгізіңіз'
        },
        ariaLabel: {
            previousMonth: 'Алдыңғы ай',
            nextMonth: 'Келесі ай',
            selectYear: 'Жылды таңдау',
            previousYear: 'Алдыңғы жыл',
            nextYear: 'Келесі жыл',
            selectMonth: 'Айды таңдау',
            selectDate: '{0}',
            currentDate: 'Бүгін, {0}'
        }
    },
    noDataText: 'Деректер жоқ',
    carousel: {
        prev: 'Алдыңғы слайд',
        next: 'Келесі слайд',
        ariaLabel: {
            delimiter: 'Слайд {0} / {1}'
        }
    },
    calendar: {
        moreEvents: 'Тағы {0}',
        today: 'Бүгін'
    },
    heatmap: {
        less: 'Азырақ',
        more: 'Көбірек'
    },
    input: {
        clear: '{0} тазалау',
        prependAction: '{0} алдыңғы әрекеті',
        appendAction: '{0} соңғы әрекеті',
        otp: 'Растау кодын енгізіңіз'
    },
    fileInput: {
        counter: 'Файлдар: {0}',
        counterSize: 'Файлдар: {0} (барлығы {1})'
    },
    fileUpload: {
        title: 'Файлдарды осында сүйреп әкеліңіз',
        divider: 'немесе',
        browse: 'Файлдарды шолу'
    },
    timePicker: {
        am: 'AM',
        pm: 'PM',
        title: 'Уақытты таңдау',
        hour: 'Сағат',
        minute: 'Минут',
        second: 'Секунд',
        notAllowed: 'Бұл мәнге рұқсат етілмеген'
    },
    pagination: {
        ariaLabel: {
            root: 'Беттер бойынша навигация',
            next: 'Келесі бет',
            previous: 'Алдыңғы бет',
            page: '{0}-бетке өту',
            currentPage: '{0}-бет, ағымдағы бет',
            first: 'Бірінші бет',
            last: 'Соңғы бет'
        }
    },
    stepper: {
        next: 'Келесі',
        prev: 'Алдыңғы'
    },
    rating: {
        ariaLabel: {
            item: 'Рейтинг {0} / {1}'
        }
    },
    loading: 'Жүктелуде...',
    infiniteScroll: {
        loadMore: 'Тағы жүктеу',
        empty: 'Басқа ештеңе жоқ'
    },
    rules: {
        required: 'Бұл өріс міндетті',
        email: 'Жарамды электрондық поштаны енгізіңіз',
        number: 'Бұл өрісте тек сандар болуы мүмкін',
        integer: 'Бұл өрісте тек бүтін сандар болуы мүмкін',
        capital: 'Бұл өрісте тек бас әріптер болуы мүмкін',
        maxLength: 'Ең көбі {0} таңба енгізу керек',
        minLength: 'Кемінде {0} таңба енгізу керек',
        strictLength: 'Енгізілген өрістің ұзындығы жарамсыз',
        exclude: '{0} таңбасына рұқсат етілмеген',
        notEmpty: 'Кемінде бір мәнді таңдаңыз',
        pattern: 'Пішім жарамсыз'
    },
    command: {
        search: 'Пәрменді теріңіз немесе іздеңіз...'
    },
    hotkey: {
        then: 'содан кейін',
        ctrl: 'Ctrl',
        command: 'Command',
        space: 'Бос орын',
        shift: 'Shift',
        alt: 'Alt',
        enter: 'Enter',
        escape: 'Escape',
        upArrow: 'Жоғары көрсеткі',
        downArrow: 'Төмен көрсеткі',
        leftArrow: 'Сол көрсеткі',
        rightArrow: 'Оң көрсеткі',
        backspace: 'Backspace',
        option: 'Option',
        plus: 'қосу',
        shortcut: 'Пернелер тіркесімі: {0}',
        or: 'немесе'
    },
    video: {
        play: 'Ойнату',
        pause: 'Кідірту',
        seek: 'Айналдыру',
        volume: 'Дыбыс деңгейі',
        showVolume: 'Дыбыс реттегішін көрсету',
        mute: 'Дыбысын өшіру',
        unmute: 'Дыбысын қосу',
        enterFullscreen: 'Толық экран',
        exitFullscreen: 'Толық экраннан шығу'
    },
    colorPicker: {
        ariaLabel: {
            eyedropper: 'Пипеткамен түсті таңдау',
            hueSlider: 'Реңк',
            alphaSlider: 'Мөлдірлік',
            redInput: 'Қызыл мәні',
            greenInput: 'Жасыл мәні',
            blueInput: 'Көк мәні',
            alphaInput: 'Мөлдірлік мәні',
            hueInput: 'Реңк мәні',
            saturationInput: 'Қанықтық мәні',
            lightnessInput: 'Ашықтық мәні',
            hexInput: 'HEX мәні',
            hexaInput: 'Мөлдірлігі бар HEX мәні',
            changeFormat: 'Түс пішімін өзгерту'
        }
    }
}

export default kk
