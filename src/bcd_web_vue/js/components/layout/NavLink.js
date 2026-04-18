/**
 * Navigation Link Component
 * Router link with active state highlighting and submenu support
 */

const { defineComponent, ref, computed, watch } = Vue;
const { useRoute } = VueRouter;

export default defineComponent({
    name: 'NavLink',

    props: {
        to: {
            type: [String, Object],
            required: true
        },
        icon: {
            type: String,
            default: ''
        },
        label: {
            type: String,
            required: true
        },
        submenu: {
            type: Array,
            default: () => []
        },
        shortcut: {
            type: String,
            default: ''
        },
        showShortcut: {
            type: Boolean,
            default: false
        }
    },

    setup(props) {
        const route = useRoute();
        const isExpanded = ref(false);

        // Check if current route matches this nav item or its submenu
        const isActive = computed(() => {
            if (props.submenu.length > 0) {
                // For parent items with submenu, check if any submenu item is active
                return props.submenu.some(item => route.path.startsWith(item.to));
            }
            return route.path === props.to || route.path.startsWith(props.to);
        });

        // Auto-expand if a submenu item is active
        watch(isActive, (newValue) => {
            if (newValue && props.submenu.length > 0) {
                isExpanded.value = true;
            }
        }, { immediate: true });

        const toggleSubmenu = (e) => {
            if (props.submenu.length > 0) {
                e.preventDefault();
                isExpanded.value = !isExpanded.value;
            }
        };

        return {
            isExpanded,
            isActive,
            toggleSubmenu
        };
    },

    template: `
        <div>
            <!-- Parent Link -->
            <router-link
                v-if="submenu.length === 0"
                :to="to"
                custom
                v-slot="{ navigate, href, isActive: linkIsActive }"
            >
                <a
                    :href="href"
                    @click="navigate"
                    class="nav-link"
                    :class="{ 'active': linkIsActive }"
                >
                    <i v-if="icon" :class="['bi', icon]"></i>
                    <span>{{ label }}</span>
                    <kbd v-if="shortcut && showShortcut" class="nav-shortcut ms-auto">{{ shortcut }}</kbd>
                </a>
            </router-link>

            <!-- Parent with Submenu -->
            <a
                v-else
                href="#"
                @click="toggleSubmenu"
                class="nav-link"
                :class="{ 'active': isActive }"
            >
                <i v-if="icon" :class="['bi', icon]"></i>
                <span>{{ label }}</span>
                <kbd v-if="shortcut && showShortcut" class="nav-shortcut me-1">{{ shortcut }}</kbd>
                <i class="bi ms-auto" :class="isExpanded ? 'bi-chevron-up' : 'bi-chevron-down'"></i>
            </a>

            <!-- Submenu Items -->
            <div v-if="submenu.length > 0 && isExpanded" class="submenu">
                <router-link
                    v-for="item in submenu"
                    :key="item.to"
                    :to="item.to"
                    custom
                    v-slot="{ navigate, href, isActive: subIsActive }"
                >
                    <a
                        :href="href"
                        @click="navigate"
                        class="nav-link submenu-link"
                        :class="{ 'active': subIsActive }"
                    >
                        <i v-if="item.icon" :class="['bi', item.icon]"></i>
                        <span>{{ item.label }}</span>
                    </a>
                </router-link>
            </div>
        </div>
    `
});
