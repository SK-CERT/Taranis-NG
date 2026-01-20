import ButtonLockMixin from './ButtonLockMixin.js';

export default {
    mixins: [ButtonLockMixin],
    props: {
        // Visual props
        icon: {
            type: Boolean,
            default: true,
            description: "Render as icon button (no label)"
        },
        text: {
            type: Boolean,
            default: false,
            description: "Render as text button"
        },
        outlined: {
            type: Boolean,
            default: false,
            description: "Render with outlined style"
        },
        small: {
            type: Boolean,
            default: false,
            description: "Render small button"
        },
        large: {
            type: Boolean,
            default: false,
            description: "Render large button"
        },
        color: {
            type: String,
            default: "",
            description: "Button color"
        },
        iconColor: {
            type: String,
            default: "",
            description: "Icon color"
        },
        customClass: {
            type: String,
            default: "",
            description: "Additional CSS classes"
        },

        // Content props
        label: {
            type: String,
            default: "",
            description: "Custom label (uses translation if empty)"
        },
        tooltip: {
            type: [String, Boolean],
            default: true,
            description: "Tooltip text or true for default translation"
        },
        customIcon: {
            type: String,
            default: "",
            description: "Custom Material Design icon"
        },
        outlinedIcon: {
            type: Boolean,
            default: false,
            description: "Use outlined icon variant"
        },

        // Behavior props
        disabled: {
            type: Boolean,
            default: false,
            description: "Disable button"
        },
        loading: {
            type: Boolean,
            default: false,
            description: "Show loading state"
        },
        dataBtn: {
            type: String,
            default: "",
            description: "Data attribute for testing/identification"
        }
    },
    computed: {
        buttonClass() {
            return this.customClass;
        },
        showIcon() {
            return this.icon || !this.icon;
        },
        showLabel() {
            return !this.icon;
        }
    },
    methods: {
        handleClick(event) {
            event.stopPropagation();
            this.$emit('click', event);
        },
        getIconFromUI(iconKey, fallback, outlinedFallback) {
            if (this.customIcon) {
                return this.customIcon;
            }
            if (this.outlinedIcon && outlinedFallback) {
                return (this.$root.UI && this.$root.UI.ICON && this.$root.UI.ICON[iconKey + '_OUTLINE']) || outlinedFallback;
            }
            return (this.$root.UI && this.$root.UI.ICON && this.$root.UI.ICON[iconKey]) || fallback;
        }
    }
}
