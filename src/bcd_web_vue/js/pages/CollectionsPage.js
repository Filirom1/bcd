/**
 * Collections Page Component
 * Displays local and network BCD collections (fonds) for peer discovery
 */

const { defineComponent, ref, onMounted } = Vue;
const { useI18n } = VueI18n;
import { apiClient } from '../api/client.js';
import HelpPanel from '../components/ui/HelpPanel.js';

export default defineComponent({
    name: 'CollectionsPage',

    components: {
        HelpPanel
    },

    setup() {
        const { t } = useI18n();

        const loading = ref(false);
        const peers = ref([]);
        const localUrl = ref('');
        const localLibraryCode = ref('');

        const loadPeers = async () => {
            try {
                loading.value = true;
                const data = await apiClient.get('/collections/peers');
                peers.value = data || [];
            } catch (error) {
                console.error('Failed to load peers:', error);
                peers.value = [];
            } finally {
                loading.value = false;
            }
        };

        const loadLocalInfo = async () => {
            try {
                const settings = await apiClient.get('/admin/settings');
                localLibraryCode.value = settings.library_code || 'BCD';
            } catch (error) {
                console.error('Failed to load local settings:', error);
                localLibraryCode.value = 'BCD';
            }
        };

        onMounted(async () => {
            localUrl.value = window.location.origin;
            await loadLocalInfo();
            await loadPeers();
        });

        return {
            t,
            loading,
            peers,
            localUrl,
            localLibraryCode,
            loadPeers
        };
    },

    template: `
        <div class="container-fluid py-4">
            <div class="d-flex justify-content-between align-items-start mb-4">
                <div>
                    <h1 class="mb-2">{{ t('collections.title') }}</h1>
                    <p class="text-muted mb-0">{{ t('collections.subtitle') }}</p>
                </div>
                <help-panel section="collections" />
            </div>

            <!-- This Collection (Local) -->
            <div class="card mb-4 border-success">
                <div class="card-header bg-success text-white">
                    <i class="bi bi-check-circle me-2"></i>
                    {{ t('collections.this_collection') }}
                </div>
                <div class="card-body">
                    <h5 class="card-title">{{ localLibraryCode }}</h5>
                    <p class="mb-0">
                        <strong>{{ t('collections.url') }}:</strong>
                        <a :href="localUrl" class="ms-2">{{ localUrl }}</a>
                    </p>
                </div>
            </div>

            <!-- Other Collections on Network -->
            <div class="card">
                <div class="card-header">
                    <i class="bi bi-diagram-3-fill me-2"></i>
                    {{ t('collections.other_collections') }}
                </div>
                <div class="card-body">
                    <!-- Loading State -->
                    <div v-if="loading" class="text-center py-4">
                        <div class="spinner-border text-primary" role="status">
                            <span class="visually-hidden">{{ t('collections.loading') }}</span>
                        </div>
                        <p class="mt-2 text-muted">{{ t('collections.loading') }}</p>
                    </div>

                    <!-- No Peers Found -->
                    <div v-else-if="peers.length === 0" class="text-muted text-center py-4">
                        <i class="bi bi-wifi-off fs-1 d-block mb-3 text-secondary"></i>
                        {{ t('collections.no_peers_found') }}
                    </div>

                    <!-- Peer Cards -->
                    <div v-else class="row g-3">
                        <div v-for="peer in peers" :key="peer.name" class="col-md-6 col-lg-4">
                            <div class="card h-100">
                                <div class="card-body">
                                    <h5 class="card-title">
                                        <i class="bi bi-book me-2 text-primary"></i>
                                        {{ peer.library_code || 'BCD' }}
                                    </h5>
                                    <p class="card-text">
                                        <small class="text-muted">{{ peer.url }}</small>
                                    </p>
                                    <a :href="peer.url" target="_blank" rel="noopener noreferrer" class="btn btn-primary btn-sm">
                                        <i class="bi bi-box-arrow-up-right me-1"></i>
                                        {{ t('collections.open_collection') }}
                                    </a>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Refresh Button -->
            <div class="mt-3">
                <button @click="loadPeers" :disabled="loading" class="btn btn-secondary">
                    <i class="bi bi-arrow-clockwise me-2" :class="{ 'spinner-border spinner-border-sm': loading }"></i>
                    {{ t('collections.refresh') }}
                </button>
            </div>
        </div>
    `
});
