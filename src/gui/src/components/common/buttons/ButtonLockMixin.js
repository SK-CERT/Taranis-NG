/**
 * Mixin for button components that support locked state
 * Provides standardized lock icon, styling, and disabled behavior
 */
export default {
    props: {
        locked: {
            type: Boolean,
            default: false,
            description: "Show lock icon and error styling"
        },
        lockColor: {
            type: String,
            default: "orange",
            description: "Color of lock icon when locked (defaults to orange)"
        }
    },
    computed: {
        effectiveColor() {
            // When locked, don't apply button background color
            return this.locked ? '' : this.color;
        },
        effectiveIconColor() {
            return this.locked ? this.lockColor : this.iconColor;
        },
        effectiveDisabled() {
            return this.locked || this.disabled;
        },
        lockIconClasses() {
            return this.locked ? 'lock-icon' : '';
        },
        lockIconStyle() {
            // Force color via inline style when locked to override disabled styling
            if (this.locked) {
                // Map common color names to their hex values
                const colorMap = {
                    'orange': '#FF9800',
                    'red': '#F44336',
                    'error': '#FF5252',
                    'blue': '#2196F3',
                    'green': '#4CAF50',
                    'yellow': '#FFEB3B',
                    'grey': '#9E9E9E',
                    'gray': '#9E9E9E'
                };
                const color = colorMap[this.lockColor] || this.lockColor;
                return `color: ${color} !important; opacity: 1 !important;`;
            }
            return '';
        }
    },
    methods: {
        getLockIcon() {
            return 'mdi-lock';
        }
    }
};
