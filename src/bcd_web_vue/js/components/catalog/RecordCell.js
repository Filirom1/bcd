/**
 * Reusable bibliographic table cell: linked title, optional subtitle/series,
 * author details, and physical-copy barcode/location/call-number metadata.
 */

const { defineComponent, computed } = Vue;
import { useGlobalModal } from '../../composables/useGlobalModal.js';
import { useAppState } from '../../composables/useAppState.js';
import { useItemBadge } from '../../composables/useItemBadge.js';

export default defineComponent({
    name: 'RecordCell',

    props: {
        recordId: {
            type: [Number, String],
            required: true
        },
        title: {
            type: String,
            required: true
        },
        openOnClick: {
            type: Boolean,
            default: true
        },
        subtitle: {
            type: String,
            default: ''
        },
        collection: {
            type: String,
            default: ''
        },
        seriesNumber: {
            type: [String, Number],
            default: ''
        },
        authors: {
            type: [String, Array],
            default: ''
        },
        itemId: {
            type: [String, Number],
            default: ''
        },
        shelfLocation: {
            type: String,
            default: ''
        },
        callNumber: {
            type: String,
            default: ''
        }
    },

    setup(props) {
        const { openRecord } = useGlobalModal();
        const { settings } = useAppState();
        const { getShelfBadge, getCoteBadge } = useItemBadge(settings);
        const authorsText = computed(() => Array.isArray(props.authors)
            ? props.authors.join(', ')
            : props.authors || '');
        const fullTitle = computed(() => [
            props.title,
            props.subtitle,
            props.collection,
            props.seriesNumber
        ].filter(Boolean).join(' : '));

        return { openRecord, getShelfBadge, getCoteBadge, authorsText, fullTitle };
    },

    template: `
        <td>
            <a
                href="#"
                @click.prevent="openOnClick && openRecord(recordId)"
                class="link-entity record-title-link fw-bold"
                :title="fullTitle"
            >
                {{ title }}<span v-if="subtitle" class="fw-normal text-muted"> : {{ subtitle }}</span><span v-if="collection" class="fw-normal text-muted"> — {{ collection }}</span><span v-if="seriesNumber" class="fw-normal text-muted">, {{ seriesNumber }}</span>
            </a>
            <div v-if="authorsText" class="small text-muted">{{ authorsText }}</div>
            <slot name="details"></slot>
            <div v-if="itemId || shelfLocation || callNumber" class="mt-1 d-flex flex-wrap align-items-center gap-1">
                <span v-if="itemId" class="small text-muted me-1">
                    <i class="bi bi-upc"></i> {{ itemId }}
                </span>
                <span v-if="shelfLocation && getShelfBadge(shelfLocation)" :style="getShelfBadge(shelfLocation)">{{ shelfLocation }}</span>
                <span v-if="callNumber && getCoteBadge(callNumber)" :style="getCoteBadge(callNumber)">{{ callNumber }}</span>
            </div>
        </td>
    `
});
