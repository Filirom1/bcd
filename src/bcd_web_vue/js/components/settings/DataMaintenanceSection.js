/**
 * Data Maintenance Section Component
 * Data cleanup and maintenance utilities for the Settings page.
 */

const { defineComponent, ref } = Vue;
const { useI18n } = VueI18n;
import { apiClient } from '../../api/client.js';
import { useNotification } from '../../composables/useNotification.js';
import { useErrorHandler } from '../../composables/useErrorHandler.js';

export default defineComponent({
    name: 'DataMaintenanceSection',

    setup() {
        const { t } = useI18n();
        const { success } = useNotification();
        const { handleError } = useErrorHandler(t);

        const settingAcquisitionDates = ref(false);

        const setAcquisitionDatesFromPublicationYear = async () => {
            if (!window.confirm(t('settings.data_maintenance_acquisition_dates_confirm'))) {
                return;
            }

            try {
                settingAcquisitionDates.value = true;
                const result = await apiClient.post('/admin/data-maintenance/set-acquisition-dates', {});
                success(t('settings.data_maintenance_acquisition_dates_success', { count: result.updated_count }));
            } catch (error) {
                handleError(error);
            } finally {
                settingAcquisitionDates.value = false;
            }
        };

        return {
            t,
            settingAcquisitionDates,
            setAcquisitionDatesFromPublicationYear
        };
    },

    template: `
        <div>
            <!-- Section header -->
            <div class="col-12 mt-4">
                <h4 class="border-bottom pb-2 mb-3">
                    <i class="bi bi-tools"></i>
                    {{ t('settings.data_maintenance_section') }}
                </h4>
            </div>

            <!-- Acquisition dates tool -->
            <div class="col-12 mb-3">
                <div class="card">
                    <div class="card-body">
                        <h5 class="card-title">
                            <i class="bi bi-calendar-check me-2"></i>
                            {{ t('settings.data_maintenance_acquisition_dates_title') }}
                        </h5>
                        <p class="card-text text-muted">
                            {{ t('settings.data_maintenance_acquisition_dates_description') }}
                        </p>
                        <button
                            class="btn btn-outline-primary"
                            @click="setAcquisitionDatesFromPublicationYear"
                            :disabled="settingAcquisitionDates"
                        >
                            <span v-if="settingAcquisitionDates" class="spinner-border spinner-border-sm me-1" role="status"></span>
                            <i v-else class="bi bi-arrow-repeat me-1"></i>
                            {{ t('settings.data_maintenance_acquisition_dates_button') }}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `
});
