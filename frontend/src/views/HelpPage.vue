<template>
  <div class="help-page">
    <header class="page-header">
      <h1>Help</h1>
      <p class="subtitle">Guides and Documentation</p>
    </header>

    <!-- Tab Bar -->
    <nav class="docs-tabs">
      <button
        v-for="tab in tabs"
        :key="tab.id"
        :class="['docs-tab', { active: activeTab === tab.id }]"
        @click="switchTab(tab.id)"
      >
        <span class="tab-icon" v-html="tab.icon"></span>
        {{ tab.label }}
      </button>
    </nav>

    <!-- Docs Layout -->
    <div class="docs-layout">
      <!-- Sidebar -->
      <aside :class="['docs-sidebar', { open: sidebarOpen }]">
        <div
          v-for="tab in tabs"
          :key="'sidebar-' + tab.id"
          :class="['docs-sidebar-panel', { active: activeTab === tab.id }]"
        >
          <h4 class="sidebar-heading">{{ tab.label }}</h4>
          <a
            v-for="section in tab.sections"
            :key="section.id"
            :href="'#' + section.id"
            :class="['sidebar-link', { active: activeSection === section.id }]"
            @click.prevent="scrollToSection(section.id)"
          >
            <span v-if="section.color" class="sidebar-color-dot" :style="{ background: section.color }"></span>
            {{ section.title }}
          </a>
        </div>
      </aside>

      <!-- Mobile sidebar backdrop -->
      <div
        v-if="sidebarOpen"
        class="sidebar-backdrop"
        @click="sidebarOpen = false"
      ></div>

      <!-- Mobile sidebar toggle -->
      <button
        class="sidebar-toggle"
        @click="sidebarOpen = !sidebarOpen"
        :aria-label="sidebarOpen ? 'Close sidebar' : 'Open sidebar'"
      >
        <svg v-if="!sidebarOpen" viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/></svg>
        <svg v-else viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
      </button>

      <!-- Content Panels -->
      <main class="docs-content">
        <div
          v-for="tab in tabs"
          :key="'panel-' + tab.id"
          :class="['docs-panel', { active: activeTab === tab.id }]"
        >
          <div
            v-for="section in tab.sections"
            :key="section.id"
            :id="section.id"
            class="docs-section"
          >
            <div class="docs-section-card">
              <!-- Title with optional color indicator -->
              <div class="section-header">
                <span v-if="section.color" class="section-color-bar" :style="{ background: section.color }"></span>
                <h2>{{ section.title }}</h2>
              </div>

              <!-- Description: string or array of strings -->
              <template v-if="Array.isArray(section.description)">
                <p v-for="(desc, di) in section.description" :key="'d'+di" class="section-description">{{ desc }}</p>
              </template>
              <p v-else-if="section.description" class="section-description">{{ section.description }}</p>

              <!-- Section-level image -->
              <div v-if="section.image" class="section-image">
                <img :src="section.image" :alt="section.imageAlt || section.title" />
              </div>

              <!-- Subsections -->
              <div
                v-for="(sub, si) in section.subsections"
                :key="si"
                :class="['docs-subsection', { 'docs-card-media': sub.image }]"
              >
                <div class="docs-card-text">
                  <h3 v-if="sub.heading">{{ sub.heading }}</h3>
                  <p v-for="(para, pi) in sub.paragraphs" :key="pi">{{ para }}</p>
                  <ol v-if="sub.criteria && sub.criteria.length" class="criteria-list">
                    <li v-for="(c, ci) in sub.criteria" :key="ci">{{ c }}</li>
                  </ol>
                  <ul v-if="sub.items && sub.items.length">
                    <li v-for="(item, ii) in sub.items" :key="ii">{{ item }}</li>
                  </ul>
                  <ul v-if="sub.statusList && sub.statusList.length" class="status-list">
                    <li v-for="(st, sti) in sub.statusList" :key="sti" class="status-list-item">
                      <span class="status-indicator" :style="{ background: st.color }"></span>
                      <span class="status-text"><strong>{{ st.label }}</strong>: {{ st.desc }}</span>
                    </li>
                  </ul>
                </div>
                <div v-if="sub.image" class="docs-card-image">
                  <img :src="sub.image" :alt="sub.imageAlt || 'Diagram'" />
                </div>
              </div>

              <!-- References footer -->
              <div v-if="section.references && section.references.length" class="section-references">
                <span class="ref-label">References:</span>
                <a
                  v-for="(ref, ri) in section.references"
                  :key="ri"
                  :href="ref.startsWith('http') ? ref : 'https://doi.org/' + ref"
                  target="_blank"
                  rel="noopener"
                  class="ref-link"
                >
                  {{ ref.startsWith('http') ? ref : 'DOI: ' + ref }}
                </a>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>

    <AppFooter />
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppFooter from '../components/AppFooter.vue'

const route = useRoute()
const router = useRouter()

const activeTab = ref('usage')
const activeSection = ref('')
const sidebarOpen = ref(false)
let observer = null

const IMG = import.meta.env.BASE_URL + 'images/help/'

const usageSections = [
  {
    id: 'usage-intro',
    title: 'Introduction',
    description: [
      'COCOMAPS-MD is a web application for analyzing non-covalent interactions at protein–protein interfaces across molecular dynamics trajectories. You upload a multi-model PDB (trajectory), choose two chains, and the server computes interface contacts frame by frame. Results are explored through contact maps, trend charts, conservation-style summaries, and structure viewing.',
      'The workflow is: upload a PDB on the home page → select two chains → optionally adjust advanced settings → start the analysis. When processing finishes, you are taken to the analysis view for that job. You can also open past jobs from the Jobs page.'
    ],
    subsections: [
      {
        heading: 'Key features',
        items: [
          'Interface-focused analysis between two protein chains over many frames.',
          'Automatic detection of chains and frame count from your PDB; long trajectories are sampled so a manageable number of frames are analyzed.',
          'Detailed categorization of interaction types (see the Interactions tab in this Help section for definitions and geometric criteria).',
          'Job list with status, search, and quick access to completed analyses.'
        ]
      }
    ]
  },
  {
    id: 'usage-upload',
    title: '1. Upload a PDB file',
    description: [
      'From the home page, provide your structure by uploading a file. The server expects a standard PDB file with the .pdb extension.',
      'Drag and drop the file onto the upload area, or click the area to open the file picker. Only one file is processed at a time. If your structure is not in PDB format, convert it to PDB before uploading.'
    ],
    subsections: [
      {
        heading: 'What happens after you choose a file',
        paragraphs: [
          'The browser reads the file to list chain identifiers found in ATOM and HETATM records, and counts trajectory frames from MODEL records. If there are no MODEL records, the structure is treated as a single frame.',
          'At least two distinct chains are required for interface analysis. If fewer than two chains are found, you will be prompted to choose a different file.'
        ]
      }
    ]
  },
  {
    id: 'usage-chains',
    title: '2. Select two chains',
    description: [
      'After a valid PDB is loaded, use Select Chains for Analysis to choose Chain 1 and Chain 2. These define the two protein chains whose mutual interface will be analyzed. The two selections must be different chains.',
      'The page shows the file name, approximate size, number of chains, and number of frames detected.',
      'If there are more than 50 frames, the home page shows a short note about how many frames will be analyzed and the step size used. Full details on step size, defaults, and custom frame ranges are under Advanced Settings → Frame sampling.'
    ],
    subsections: []
  },
  {
    id: 'usage-advanced',
    title: '3. Advanced Settings',
    description: [
      'Open the Advanced Settings section to optionally customize the job. Defaults are appropriate for most runs.',
      'Geometric thresholds for each interaction class (hydrogen bonds, π-stacking, and so on) are fixed for a given server configurationm, they are documented under Help → Interactions.'
    ],
    subsections: [
      {
        heading: 'Job name',
        paragraphs: [
          'Job name identifies the run in the Jobs list and in analysis views. By default it is the same as your PDB file name (without the .pdb extension), unless you type a different value.'
        ]
      },
      {
        heading: 'Email',
        paragraphs: [
          'Optionally enter your email address. When you submit a job, you will receive an email containing the job ID and a link to the job.'
        ]
      },
      {
        heading: 'Use Reduce',
        paragraphs: [
          'When enabled, structures can be preprocessed to add hydrogens using Reduce before analysis. This can improve consistency for structures that lack hydrogens at the cost of longer runtime.',
          'Reference: Word, J. M., Lovell, S. C., Richardson, J. S., & Richardson, D. C. (1999). Asparagine and glutamine: Using hydrogen atom contacts in the choice of side-chain amide orientation. J. Mol. Biol. 285, 1735\u20131747.'
        ]
      },
      {
        heading: 'Time unit',
        paragraphs: [
          'An optional label (for example ns or ps) is used for time-like axes in charts when provided. If left empty, axes are labeled in frames.'
        ]
      },
      {
        heading: 'Frame sampling',
        paragraphs: [
          'When the trajectory contains more than 50 frames, the interface does not analyze every frame by default. Step size controls subsampling: only a subset of frames are sent to the analysis, taken at regular intervals from the first frame to the last.',
          'What step size means: a step size of N keeps every Nth frame in order. For example, step 2 keeps frames 1, 3, 5, … (every other frame); step 10 keeps frames 1, 11, 21, … Larger steps mean fewer, more widely spaced samples. Step 1 means every frame—which is appropriate when you have at most 50 frames overall, or when you use a short custom range in this section.',
          'Default: the app sets the step size automatically so that spanning the full trajectory yields roughly on the order of 50 analyzed frames (the step is derived from the total frame count). Before you open Advanced Settings, a short note on the home page already states how many frames will be analyzed and which step size is used.',
          'The Step size field in Advanced Settings matches that default and can be changed: increase the step to lighten the job or decrease it for denser sampling. Use custom interval turns off regular stepping across the entire trajectory and lets you pick a specific start and end frame (within the limits shown). The panel displays how many frames will be analyzed for your current choices.'
        ]
      }
    ]
  },
  {
    id: 'usage-run',
    title: '4. Run the analysis',
    description: [
      'When Chain 1 and Chain 2 are set, Start Analysis becomes available. Click it to upload the file and queue the job on the server.',
      'Progress appears on the same page with a progress indicator. The page URL may include a job query parameter so that refreshing the browser can resume tracking that run.',
      'When the job completes successfully, you are redirected to the analysis view for that result. If the analysis URL cannot be resolved, you may be sent to the Jobs page instead. If the job fails, an error message is shown on the home page.',
      'To use a different structure, use Change on the file card to clear the upload and start over.'
    ],
    subsections: []
  },
  {
    id: 'usage-jobs',
    title: 'Jobs page',
    description: [
      'Open Jobs from the navigation bar to see all your jobs in a searchable, sortable table: status, name, creation date, and frame count.',
      'Use Submit a new job to return to the home page and upload another PDB.'
    ],
    subsections: [
      {
        heading: 'Job status',
        paragraphs: [
          'Each job row shows a colored icon reflecting its current state:'
        ],
        statusList: [
          { label: 'Completed', color: '#34c759', desc: 'The analysis finished successfully. Click the row to open the results in the analysis view.' },
          { label: 'Processing', color: '#ff9500', desc: 'The job is still running. Click the row to return to the home page and track its progress in real time.' },
          { label: 'Failed', color: '#ff3b30', desc: 'The analysis encountered an error. The row is not clickable; you can submit a new job instead.' }
        ]
      }
    ]
  }
]

const interactionSections = [
  {
    id: 'int-overview',
    title: 'Overview',
    description: 'CoCoMaps-MD identifies and classifies 18 types of atomic interactions at molecular interfaces. These include 16 specific interaction types defined by precise geometric criteria, plus proximal contacts and clashes. Each section below describes the interaction and its detection criteria.',
    subsections: []
  },
  {
    id: 'int-table',
    title: 'Table of Atomic Interactions',
    description: [
      'Based on a cut-off distance between any pair of heavy (non-hydrogen) atoms from the chains whose interaction interface is under analysis, an overall analysis of residues contacting each other at the interface is derived. The default cut-off value is 5 \u00C5.',
      'Each pair of contacting residues at the interface is tagged with its associated specific atomic interactions, as detailed below. All contacts occurring within the cut-off distance and not falling in any class of the considered atomic interactions, are categorized as \u201CProximal contacts\u201D (see below).',
      'In the interactions table, each interaction type can be toggled on or off. By default, Proximal contacts is turned off: the table initially includes the other interaction classes only, so you can focus on specific interaction types first. Turn Proximal contacts on when you also want to see contacts that fall only in that category.'
    ],
    image: IMG + 'interactions-table-proximal.png',
    imageAlt: 'Interactions table with Proximal contacts toggle off by default',
    subsections: [
      {
        paragraphs: [
          'In the following, all the types of atomic interactions identified and visualized by the web server are listed.'
        ]
      }
    ]
  },
  {
    id: 'int-hbonds',
    title: 'H-bonds',
    color: '#2196F3',
    description: 'Hydrogen bonds form due to an electrostatic attraction between a hydrogen atom covalently bonded to a highly electronegative atom, such as O or N (H-bond donor, D) and another non-covalently bonded electronegative atom (H-bond acceptor, A). Detected using HBPLUS v3.2.',
    image: IMG + 'h-bond.png',
    imageAlt: 'H-bond interaction diagram',
    references: ['10.1006/jmbi.1994.1334'],
    subsections: [
      {
        heading: 'Detection Criteria',
        paragraphs: ['The following geometric criteria are applied:'],
        criteria: [
          'The distance between the donor (D) and the acceptor (A) atoms must be within 4.0 Å.',
          'The θ angle formed by the donor (D), hydrogen (H), and acceptor (A) atoms must exceed 90°.'
        ],
      }
    ]
  },
  {
    id: 'int-salt-bridges',
    title: 'Salt-bridges',
    color: '#E91E63',
    description: [
      'Salt-bridges are strong electrostatic attractions between positively and negatively charged atoms. They form between NH₃⁺ groups and COO⁻ groups.',
      'For protein-protein interactions, they are identified between Lys/Arg (positive) and Asp/Glu (negative) side chains. For protein-nucleic acid complexes, the negative charges come from nucleotide phosphate groups (OP1/OP2). Detected using HBPLUS v3.2.'
    ],
    image: IMG + 'salt-bridge.png',
    imageAlt: 'Salt-bridge interaction diagram',
    references: ['10.1006/jmbi.1994.1334'],
    subsections: [
      {
        heading: 'Detection Criteria',
        paragraphs: [],
        criteria: [
          'The distance between the positive and negative charged atoms must be within 4.5 Å.'
        ],
      }
    ]
  },
  {
    id: 'int-water-mediated',
    title: 'Water-mediated contacts',
    color: '#00BCD4',
    description: 'Water molecules act as bridges between two electronegative atoms by H-bonding to them, contributing to overall complex stability. Detected using HBPLUS v3.2.',
    image: IMG + 'water-mediated.png',
    imageAlt: 'Water-mediated contact diagram',
    references: ['10.1006/jmbi.1994.1334', '10.1002/prot.24439'],
    subsections: [
      {
        heading: 'Detection Criteria',
        paragraphs: [],
        criteria: [
          'The distance between the water oxygen and H-bonded electronegative atoms must be within 4.0 Å.'
        ],
      }
    ]
  },
  {
    id: 'int-ch-on',
    title: 'CH-O/N bonds',
    color: '#8BC34A',
    description: 'Weak electrostatic attraction between a hydrogen atom covalently bonded to C (donor) and an electronegative atom X (O or N, acceptor). Weaker than proper H-bonds but play important roles in supramolecular chemistry and molecular recognition.',
    image: IMG + 'ch-on.png',
    imageAlt: 'CH-O/N bond diagram',
    references: ['10.1021/ar950135n', 'https://journals.iucr.org/services/cif/hbonds.html'],
    subsections: [
      {
        heading: 'Detection Criteria',
        paragraphs: [],
        criteria: [
          'The distance d(C–X) must be within 4.0 Å.',
          'The angle θ(C-H-X) must exceed 110°.'
        ],
      }
    ]
  },
  {
    id: 'int-ss-bonds',
    title: 'Disulfide bridges (S-S bonds)',
    color: '#FFC107',
    description: 'The only covalent bonds considered in this analysis. They form intra- or inter-molecularly between sulfur atoms at the γ position (SG) of Cysteine side chains.',
    image: IMG + 'ss-bonds.png',
    imageAlt: 'Disulfide bridge diagram',
    references: ['10.1016/0022-2836(81)90515-5'],
    subsections: [
      {
        heading: 'Detection Criteria',
        paragraphs: [],
        criteria: [
          'The SG–SG distance must be within 3.0 Å.'
        ],
      }
    ]
  },
  {
    id: 'int-halogen',
    title: 'Halogen bonds',
    color: '#9C27B0',
    description: 'Non-covalent interactions from electrostatic attraction between a halogen atom Z (F, Cl, Br, I) covalently bonded to C, and an electronegative atom X (O, N, S) covalently bonded to a C/P/S (Y) atom.',
    image: IMG + 'halogen-bonds.png',
    imageAlt: 'Halogen bond diagram',
    references: ['10.1073/pnas.0407607101'],
    subsections: [
      {
        heading: 'Detection Criteria',
        paragraphs: [],
        criteria: [
          'The X–Z distance must be within the sum of their van der Waals radii.',
          'The angle θ₁(C-Z-X) must exceed 165°.',
          'The angle θ₂(Z-X-Y) must exceed 120°.'
        ],
      }
    ]
  },
  {
    id: 'int-metal',
    title: 'Metal-mediated contacts',
    color: '#795548',
    description: 'Metal cations (M) act as bridges between two molecules by coordinating to electronegative atoms X (O, N, S). Van der Waals radii are not used here due to uncertainties about the charge and oxidation state of metal ions in the structures.',
    image: IMG + 'metal-mediated.png',
    imageAlt: 'Metal-mediated contact diagram',
    references: ['10.1002/pro.727'],
    subsections: [
      {
        heading: 'Detection Criteria',
        paragraphs: [],
        criteria: [
          'The M–X distance must be within 3.2 Å.'
        ],
      }
    ]
  },
  {
    id: 'int-pi-framework',
    title: 'Geometrical Framework for π Interactions',
    description: [
      '\u03C0 (Pi) interactions may involve the \u03C0 cloud of the single or double aromatic ring of the nucleobases: G, U, A, T/U in nucleic acids, and aromatic rings of the amino acids: His, Phe, Trp, and Tyr in proteins. To detect such interactions, we set up a geometrical frame on the \u03C0 rings, both single and double, as detailed below.',
      'For each aromatic ring, we assign its geometrical center (centroid), then define a ring plane (shown as a gray grid in the figure below), passing through the above centroid and the two ring atoms listed first in the corresponding .pdb/.cif file. Then, to define whether an interaction exists between a given atom/ion and the aromatic ring, we orthogonally project the atom into the ring plane and measure this orthogonal distance. The interaction is assigned if: i) the orthogonal distance is within a given threshold, and ii) the projection falls within the perimeter of the ring (to this aim we use the ConvexHull function available from the SciPy library in Python).'
    ],
    references: ['https://docs.scipy.org/doc/scipy/reference/generated/scipy.spatial.ConvexHull.html'],
    subsections: []
  },
  {
    id: 'int-cation-pi',
    title: 'Cation-π interactions',
    color: '#FF5722',
    description: 'Attraction between a positive charge (cation) and the π cloud of an aromatic ring. The positive charges on the side chains of Arg (NE, CZ, NH1, NH2) and Lys (CE, NZ) are considered as cations.',
    image: IMG + 'cation-pi.png',
    imageAlt: 'Cation-π interaction diagram',
    references: ['10.1093/nar/gkh733'],
    subsections: [
      {
        heading: 'Detection Criteria',
        paragraphs: [],
        criteria: [
          'The vertical distance from the cation to the ring plane must be within 5.0 Å.'
        ],
      }
    ]
  },
  {
    id: 'int-anion-pi',
    title: 'Anion-π interactions',
    color: '#F44336',
    description: 'Attraction between a negative charge (anion) and the π cloud of an aromatic ring. The negative charges on the side chains of Glu (OE1, OE2) and Asp (OD1, OD2), and on DNA/RNA phosphate groups (OP1/OP2) are considered.',
    image: IMG + 'anion-pi.png',
    imageAlt: 'Anion-π interaction diagram',
    references: ['10.1093/nar/gkx757'],
    subsections: [
      {
        heading: 'Detection Criteria',
        paragraphs: [],
        criteria: [
          'The vertical distance from the anion to the ring plane must be within 5.0 Å.'
        ],
      }
    ]
  },
  {
    id: 'int-amino-pi',
    title: 'Amino-π interactions',
    color: '#3F51B5',
    description: 'Attractive forces between an amino group and the π-electron cloud of an aromatic ring. Amino atoms considered: ND1 of Asn, NE2 of Gln, N2 of guanine (G), N6 of adenine (A), and N4 of cytosine (C).',
    image: IMG + 'amino-pi.png',
    imageAlt: 'Amino-π interaction diagram',
    references: ['10.1002/prot.24527'],
    subsections: [
      {
        heading: 'Detection Criteria',
        paragraphs: [],
        criteria: [
          'The vertical distance from the amino atom to the ring plane must be within 5.0 Å.'
        ],
      }
    ]
  },
  {
    id: 'int-lp-pi',
    title: 'lp-π interactions',
    color: '#009688',
    description: 'Attraction between an electric lone pair (on atom LP) and the π cloud of an aromatic ring. Lone-pair-presenting atoms considered are any O, S, N atoms featuring at least one electron lone pair.',
    image: IMG + 'lp-pi.png',
    imageAlt: 'lp-π interaction diagram',
    references: ['10.1093/nar/gkx757'],
    subsections: [
      {
        heading: 'Detection Criteria',
        paragraphs: [],
        criteria: [
          'The vertical distance from the lone-pair-presenting atom to the ring plane must be within 5.0 Å.'
        ],
      }
    ]
  },
  {
    id: 'int-pi-pi',
    title: 'π-π stacking',
    color: '#673AB7',
    description: 'Attraction between the π clouds of aromatic rings in close proximity. Three geometric parameters (distance and two angles) characterize the intermolecular orientation of the rings.',
    image: IMG + 'pi-pi.png',
    imageAlt: 'π-π stacking diagram',
    references: ['10.1074/jbc.273.25.15458'],
    subsections: [
      {
        heading: 'Detection Criteria',
        paragraphs: [],
        criteria: [
          'The centroid-to-centroid distance between the two rings must be within 5.5 Å.',
          'The center-normal angle (θ) must be within 80°.',
          'The normal-normal angle (γ) must be within 90°.'
        ],
      }
    ]
  },
  {
    id: 'int-ch-pi',
    title: 'CH-π interactions',
    color: '#4CAF50',
    description: 'Attraction between a hydrogen atom covalently bonded to C and the π cloud of an aromatic ring. Relatively weak but can significantly contribute to the stability of molecular complexes.',
    image: IMG + 'ch-pi.png',
    imageAlt: 'CH-π interaction diagram',
    references: ['10.1006/jmbi.2000.4473'],
    subsections: [
      {
        heading: 'Detection Criteria',
        paragraphs: [],
        criteria: [
          'The distance from C to the ring centroid (πm) must be within 4.5 Å.',
          'The angle θ₁(C-πm-πn) must be within 30°.',
          'The angle θ₂ between the C-H bond and the H-πm vector must be at least 120°.'
        ],
      }
    ]
  },
  {
    id: 'int-onsh-pi',
    title: 'O/N/SH-π interactions',
    color: '#FF9800',
    description: 'Attraction between a hydrogen atom covalently bonded to O, N, or S (atom X) and the π-cloud of an aromatic ring.',
    image: IMG + 'onsh-pi.png',
    imageAlt: 'O/N/SH-π interaction diagram',
    references: ['10.1006/jmbi.2000.4301', '10.1093/nar/gkg528'],
    subsections: [
      {
        heading: 'Detection Criteria',
        paragraphs: [],
        criteria: [
          'The distance from X to the ring origin must be within 4.5 Å.',
          'The angle θ₁(X-origin-z) must be within 30°.',
          'The angle θ₂ between the X-H bond and the H-origin vector must be at least 120°.'
        ],
      }
    ]
  },
  {
    id: 'int-apolar',
    title: 'Apolar vdW contacts',
    color: '#607D8B',
    description: 'Van der Waals interactions between two apolar atoms (C atoms bonded only to C or H). Apolar interactions between π-π stacking rings are excluded from this category.',
    image: IMG + 'apolar.png',
    imageAlt: 'Apolar vdW contact diagram',
    references: ['10.1093/nar/gkv315'],
    subsections: [
      {
        heading: 'Detection Criteria',
        paragraphs: [],
        criteria: [
          'The distance must be within the sum of van der Waals radii + 0.5 Å tolerance (for C at 1.7 Å, this gives a cutoff of 3.9 Å).'
        ],
      }
    ]
  },
  {
    id: 'int-polar',
    title: 'Polar vdW contacts',
    color: '#9E9E9E',
    description: 'Van der Waals interactions between two atoms where at least one is not apolar. Polar interactions between π-π stacking rings are excluded from this category.',
    image: IMG + 'polar.png',
    imageAlt: 'Polar vdW contact diagram',
    references: ['10.1093/nar/gkv315'],
    subsections: [
      {
        heading: 'Detection Criteria',
        paragraphs: [],
        criteria: [
          'The distance must be within the sum of van der Waals radii + 0.5 Å tolerance.'
        ],
      }
    ]
  },
  {
    id: 'int-proximal',
    title: 'Proximal contacts',
    color: '#BDBDBD',
    description: 'All contacts within the cut-off distance (5 Å by default) that do not fall into any of the specific interaction classes above.',
    references: ['10.1016/j.jmb.2016.12.004'],
    subsections: []
  },
  {
    id: 'int-clashes',
    title: 'Clashes',
    color: '#D32F2F',
    description: 'Contacts between heavy atoms occurring at a distance below the sum of their van der Waals radii, indicating steric overlap.',
    references: ['10.1016/j.jmb.2016.12.004'],
    subsections: []
  },
  {
    id: 'int-vdw-radii',
    title: 'Van der Waals radii',
    subsections: [
      {
        items: [
          'Br \u2013 1.85 \u00C5',
          'C \u2013 1.70 \u00C5',
          'Cl \u2013 1.75 \u00C5',
          'F \u2013 1.47 \u00C5',
          'I \u2013 1.98 \u00C5',
          'N \u2013 1.55 \u00C5',
          'O \u2013 1.52 \u00C5',
          'S \u2013 1.80 \u00C5',
          'P \u2013 1.80 \u00C5'
        ]
      }
    ]
  },
  {
    id: 'int-detection-tools',
    title: 'Interaction detection',
    subsections: [
      {
        items: [
          'Reduce v4.14 \u2013 for adding hydrogen atoms to proteins and nucleic acids.',
          'HBPLUS v3.2 \u2013 for detecting hydrogen bonds and water-mediated contacts.',
          'NACCESS v2.1.1 \u2013 for solvent accessible surface area calculations.',
          'HBADD \u2013 for additional hydrogen bond analyses.'
        ]
      }
    ]
  },
  {
    id: 'int-overlap',
    title: 'Handling of overlapping classifications',
    description: 'When more than one interaction type is detected for a residue pair, we apply the following hierarchy:',
    subsections: [
      {
        items: [
          'If \u03C0\u2013\u03C0 stacking is present together with apolar van der Waals (vdW) contacts, only the \u03C0\u2013\u03C0 stacking is retained.',
          'If both a salt bridge and a hydrogen bond are identified for the same atom pair, the contact will be classified as a salt bridge.',
          'If hydrogen bonds, halogen bonds, or weak H-bonds coexist with polar vdW contacts, only the directional bonds are kept.'
        ],
        paragraphs: [
          'Clashes are defined when the observed interatomic distance is less than the sum of the van der Waals radii. If the interaction also falls into one of the standard categories (e.g., hydrogen bond, CH\u2013O/N bond, polar/apolar vdW, halogen bond, disulfide bond, salt bridge), it is reported with an asterisk alongside the respective interaction label.'
        ]
      }
    ]
  },
  {
    id: 'int-interface-area',
    title: 'Interface area and residues',
    description: [
      'Buried surface areas are calculated with NACCESS. Residues at the interface are defined as those having an ASA (Accessible Surface Area) decreased by > 1.0 \u00C5\u00B2 upon the complex formation.',
      'POLAR and NON POLAR interface percentages (%) refer to the calculated interface area (\u00C5\u00B2) for the complex and sum up to 100.',
      'In the ASA tables for chain 1 & 2, ASA values in the complex and in the isolated molecule (\u201Cfree\u201D), along with the difference between them are reported for each residue.'
    ],
    references: ['https://wolf.bms.umist.ac.uk/naccess/'],
    subsections: [
      {
        paragraphs: [
          'Reference: Hubbard, S. J. and Thornton, J. M. \u201CNACCESS\u201D Computer Program, 1993.'
        ]
      }
    ]
  }
]

const legendsSections = [
  {
    id: 'legends-abbreviations-units',
    title: 'Abbreviations & Units',
    description: [
      'Several abbreviations and symbols are used throughout the application. The following glossary explains the meaning of each symbol and the context in which it appears.'
    ],
    subsections: [
      {
        heading: 'Area & Conservation metrics',
        items: [
          'BSA \u2013 Buried Surface Area. The surface area of the protein\u2013protein interface that becomes inaccessible to solvent upon complex formation. Measured in \u00C5\u00B2 and displayed in the Area Composition chart.',
          'CR (Conserved Residues) \u2013 the number of unique residue pairs that appear in at least the specified percentage of trajectory frames. The subscript indicates the active pair conservation threshold (e.g. CR\u2085\u2080 at 50%).',
          'CA (Conserved Atomic interactions) \u2013 the number of pair\u2013type combinations (e.g., A-LYS8 \u2013 B-ASP45 via H-bond) that meet the interaction type conservation threshold.'
        ]
      },
      {
        heading: 'Units of measurement',
        items: [
          '\u00C5 (Ångström) \u2013 a unit of length equal to 10\u207B\u00B9\u2070 m. Used for interatomic distances and distance cutoff thresholds throughout the analysis.',
          'vdW (van der Waals) \u2013 refers to van der Waals radii. The sum of the vdW radii of two atoms is used as a reference distance for detecting clashes and apolar contacts.',
          'ns, ps, fs, \u03BCs \u2013 nanoseconds, picoseconds, femtoseconds, and microseconds. These time units may appear on chart axes if a time unit label was configured at job submission. If none is provided, axes default to frame numbers.'
        ]
      },
      {
        heading: 'Identifiers',
        items: [
          'PDB \u2013 Protein Data Bank, the standard file format for structural data. The application accepts trajectory files in .pdb format containing MODEL records.',
          'Atom type symbols \u2013 P (Phosphorus), N (Nitrogen), S (Sulfur), O (Oxygen), H (Hydrogen). These appear in atomic-level details in trajectory analysis panels.'
        ]
      }
    ]
  },
  {
    id: 'legends-residue-notation',
    title: 'Residue Notation',
    description: [
      'Residues are identified using a standardised notation that combines the amino acid name, sequence number, and chain identifier to ensure unambiguous references across all charts and panels.'
    ],
    subsections: [
      {
        heading: 'Individual residues',
        paragraphs: [
          'Residues are formatted as: RESNAMENUM\u2082CHAIN (for example, LYS8\u2082A or ASP45\u2082B).'
        ],
        items: [
          'RESNAME \u2013 the three-letter amino acid code (e.g., LYS for lysine, ASP for aspartic acid).',
          'NUM \u2013 the residue sequence number from the PDB file.',
          'CHAIN \u2013 the chain identifier (a single letter or character) from the PDB file.',
          'A hyphen prefixes the chain identifier for the second residue in a pair (e.g., B-ASP45) to signal that the residue belongs to a different chain.'
        ]
      },
      {
        heading: 'Residue pairs',
        paragraphs: [
          'Interactions are between two residues, displayed as: LYS8\u2082A \u2194 B-ASP45\u2082B.'
        ],
        items: [
          'The \u2194 symbol is used as the delimiter to visually separate the two residues in a cross-chain pair.',
          'This format is used consistently across the conservation matrix, trajectory analysis panels, ranking cards, and conservation analysis summaries.'
        ]
      }
    ]
  },
  {
    id: 'legends-conservation-modifiers',
    title: 'Conservation Modifiers & Suffixes',
    description: [
      'Special notations in the analysis results indicate additional properties of detected contacts or reflect the active threshold settings.'
    ],
    subsections: [
      {
        heading: 'Asterisk superscript',
        paragraphs: [
          'An asterisk (*) next to an interaction type label indicates that the same pair of atoms also qualifies as a clash\u2014that is, the interatomic distance falls below the sum of the van der Waals radii of the two atoms. This marks contacts that may be sterically strained or unusually close.'
        ]
      },
      {
        heading: 'Threshold subscripts',
        paragraphs: [
          'Conservation metrics display a subscript to indicate the threshold at which they are computed.'
        ],
        items: [
          'CR\u2085\u2080 \u2013 Conserved Residues computed at 50% pair conservation threshold. The subscript changes to match the value selected via the Pair Conservation Threshold slider (e.g., CR\u2087\u2080 at 70%).',
          'CA\u2085\u2080 \u2013 Conserved Atomic interactions computed at 50% type conservation threshold. The subscript reflects the Interaction Type Conservation Threshold setting.',
          'Changing the threshold sliders on the controls panel updates these subscripts in real time across all summary cards.'
        ]
      }
    ]
  },
  {
    id: 'legends-conservation-rankings',
    title: 'Conservation Analysis Rankings',
    description: [
      'The Conservation Analysis panel at the bottom of each chart page presents three ranked lists that summarise the most notable contacts at the interface.'
    ],
    subsections: [
      {
        heading: 'Most Conserved Pairs',
        paragraphs: [
          'Ranking of residue pairs by their average conservation across all interaction types they participate in. A pair that forms multiple interaction types at high conservation will rank higher.'
        ],
        items: [
          'Each entry shows the residue pair, the number of frames it was detected in, and coloured interaction type tags.',
          'Coloured type tags use the global interaction palette. Hovering over a tag reveals the exact conservation: \u201cType \u2014 XX% (Y/Z frames)\u201d.',
          'Clicking the \u201c+N more\u201d button opens a modal with the complete ranked list.'
        ]
      },
      {
        heading: 'Longest Conserved Stretch',
        paragraphs: [
          'Ranking of pairs by the maximum number of consecutive frames during which at least one interaction type persisted without interruption. This identifies sustained contacts, even if their overall frequency across the whole trajectory is moderate.'
        ],
        items: [
          'A long consecutive stretch suggests a structurally stable contact that may serve as an anchor point at the interface.'
        ]
      },
      {
        heading: 'Most Conserved Types',
        paragraphs: [
          'Ranking of interaction types by their average conservation across all pairs at the interface. This reveals which molecular forces (e.g., hydrogen bonds, \u03C0-\u03C0 stacking) dominate the interface overall.'
        ],
        items: [
          'A highly conserved type indicates a pervasive interaction mechanism at the interface, independent of the specific residues involved.'
        ]
      }
    ]
  }
]

const chartsSections = [
  {
    id: 'chart-conservation-matrix',
    title: 'Interaction Conservation Matrix',
    description: [
      'A comprehensive heatmap that visualises how consistently each residue pair interacts across all interaction types throughout the trajectory. The chart lets you see at a glance which contacts persist and which change over time.',
      'Alongside the matrix, an Atom Change Detection mode highlights where new interactions appear or existing ones break when you move from frame to frame.'
    ],
    image: IMG + 'screenshots/interaction-conservation-matrix.png',
    imageAlt: 'Interaction conservation matrix heatmap with color-coded interaction types',
    subsections: [
      {
        heading: 'What it shows',
        paragraphs: [
          'Rows represent individual residue pairs (e.g., A-LYS8 \u2013 B-ASP45). Each column corresponds to a specific interaction type and is coloured according to the global interaction palette. A filled cell means that the pair forms that interaction type in at least the minimum percentage of frames defined by the Interaction Type Conservation Threshold.',
          'Hovering over a cell reveals the exact conservation percentage for that pair\u2013type combination.'
        ]
      },
      {
        heading: 'How to read it',
        paragraphs: [
          'A densely filled row means a pair forms many different interaction types over the trajectory. A sparsely filled row means the pair is less versatile or short-lived. Click the legend items to show or hide individual interaction types.'
        ]
      },
      {
        heading: 'Filters: Conservation thresholds',
        paragraphs: [
          'Two sliders control which data are displayed.'
        ],
        items: [
          'Pair Conservation Threshold \u2013 sets the minimum percentage of frames a residue pair must be present in to appear at all (0\u2013100%). Raising this removes infrequent pairs.',
          'Interaction Type Conservation Threshold \u2013 sets the minimum percentage of frames a specific interaction type must persist in for a given pair to show a cell (50\u2013100%).'
        ]
      },
      {
        heading: 'Atom Change Detection Mode',
        paragraphs: [
          'A selector above the chart lets you choose what the overlay dots are compared against. Changes are highlighted as orange dots with connecting lines on the heatmap. Three comparison modes are available:'
        ],
        items: [
          'Previous Frame \u2013 highlights atom-level differences between the current frame and the immediately preceding frame.',
          'Most Dominant Atom Pair \u2013 compares the current frame with the most frequently occurring atom pair for that cell across the whole trajectory.',
          'First Frame \u2013 compares the current frame with the first frame in which that interaction appears, using it as a baseline.'
        ]
      },
      {
        heading: 'Trajectory Analysis',
        paragraphs: [
          'Clicking any heatmap cell opens the Trajectory Analysis panel. This modal shows the binary timeline (present or absent) for that specific residue pair and interaction type across every frame of the simulation.',
          'The timeline bar at the top uses blue segments for frames where the interaction is present and gray for absent frames. Click on any segment to highlight it and see atom-level details for that frame\u2014which atoms are connected, bond distance, and the individual conservation of each atom pair.',
          'Statistical summary cards show the overall persistence, average distance, and the longest consecutive stretch where the interaction persists without interruption.'
        ]
      }
    ]
  },
  {
    id: 'chart-heatmap',
    title: 'Interaction Heatmap',
    description: [
      'A residue\u2013residue contact map that summarises the full interface between the two chains. Each cell represents a pair of residues, coloured by how frequently that pair interacts across the analysed frames.'
    ],
    image: IMG + 'screenshots/heatmap.png',
    imageAlt: 'Interaction heatmap contact map between Chain A and Chain B',
    subsections: [
      {
        heading: 'What it shows',
        paragraphs: [
          'The x-axis lists residues from Chain A and the y-axis lists residues from Chain B. The colour intensity of each cell encodes the interaction consistency\u2014the proportion of frames in which that pair is in contact\u2014ranging from light gray (rare) to deep blue (persistent).'
        ]
      },
      {
        heading: 'How to read it',
        paragraphs: [
          'A compact, continuous hotspot (a dark block or diagonal band) suggests a stable interface patch. Scattered dots indicate transient or localised contacts. Hover over a cell to see the pair name, list of interaction types, and the number of frames it appeared in.'
        ]
      },
      {
        heading: 'Controls',
        paragraphs: [
          'A toggle switch lets you choose how residue labels are displayed.'
        ],
        items: [
          'Full labels (default) \u2013 shows the full residue identifier (e.g., A-LYS8) for maximum clarity when there are few residues.',
          'Numbers only \u2013 shows only the sequence number for compactness on larger interfaces.',
          'The main interaction type filter and conservation threshold slider in the global Controls Panel above the chart also apply to this heatmap.'
        ]
      }
    ]
  },
  {
    id: 'chart-interaction-trends',
    title: 'Interaction Trends',
    description: [
      'A line chart that tracks the evolution of interaction counts at the interface over the trajectory timeline. It shows how many contacts of each type exist frame by frame, making it easy to spot trends such as stable contacts, sudden disruptions, or gradual shifts in interaction composition.'
    ],
    image: IMG + 'screenshots/interaction-trends.png',
    imageAlt: 'Interaction trends line chart showing interaction counts over time',
    subsections: [
      {
        heading: 'What it shows',
        paragraphs: [
          'Each coloured line corresponds to one of the 18 interaction types, coloured consistently with the rest of the application. The x-axis represents frames (or a time unit such as ns or ps if configured). The y-axis shows the count of contacts of that interaction type in each frame.'
        ]
      },
      {
        heading: 'How to read it',
        paragraphs: [
          'A flat, persistent line indicates a stable interaction throughout the simulation. Spikes suggest brief but intense events. A declining trend may indicate structural rearrangement. Multiple lines with similar trajectories suggest coupling between interaction types.',
          'The lines are sorted so that the most active interaction types are drawn first, ensuring they remain visible on top.'
        ]
      },
      {
        heading: 'Controls',
        items: [
          'Interaction Type Conservation Threshold slider \u2013 filters out interaction types that do not meet the minimum conservation requirement, reducing visual clutter on long trajectories.',
          'Log scale toggle \u2013 available via the global Controls Panel, useful when interaction counts span several orders of magnitude.',
          'Time unit \u2013 the x-axis label reflects the configured time unit (frames, ns, ps) if one was provided during job submission.'
        ]
      }
    ]
  },
  {
    id: 'chart-distance-distribution',
    title: 'Distance Distribution',
    description: [
      'Violin plots showing the distribution of interatomic distances between residue pairs, broken down by interaction type. This view reveals not just the average separation of paired residues, but the spread and density of their distances over the full trajectory.'
    ],
    image: IMG + 'screenshots/distance-distribution.png',
    imageAlt: 'Distance distribution violin plots with global mean overlay',
    subsections: [
      {
        heading: 'What it shows',
        paragraphs: [
          'Each violin represents the distance distribution of a single residue pair for the selected interaction type. The width of the violin at a given distance indicates how frequently that distance occurs. A narrow, tall violin means the pair stays at a very consistent distance; a wide, short violin indicates more variability.'
        ]
      },
      {
        heading: 'How to read it',
        paragraphs: [
          'A dashed horizontal line marks the global mean distance across all displayed pairs. Individual mean markers (small dots) show where each pair\u2019s average falls. Pairs clustered near the global mean are typical of the interface, while outliers may represent unusually tight or loose contacts.'
        ]
      },
      {
        heading: 'Controls',
        items: [
          'Interaction Type Filter Chips \u2013 colour-coded buttons at the top of the chart let you select one or more interaction types to display. Click to include; click an active chip to remove.',
          'Pair Conservation Threshold slider \u2013 filters pairs by their overall conservation, from 0% to 100%. The chart is limited to the top 50 pairs by conservation to maintain rendering performance.',
          'Hover tooltips \u2013 hovering over a violin displays the residue pair name and the number of frames contributing to the plot.'
        ]
      }
    ]
  },
  {
    id: 'chart-area-composition',
    title: 'Area Composition',
    description: [
      'Tracks the Buried Surface Area (BSA) at the protein\u2013protein interface across frames. BSA is a key indicator of interface stability and provides a macroscopic complement to the per-residue interaction data.'
    ],
    image: IMG + 'screenshots/area-composition.png',
    imageAlt: 'Buried Surface Area chart showing total, polar, and non-polar composition over frames',
    subsections: [
      {
        heading: 'What it shows',
        paragraphs: [
          'Three overlaid series track the interface area over time:'
        ],
        items: [
          'Total BSA (solid blue line) \u2013 the total buried surface area of the interface in \u00C5\u00B2.',
          'Polar Buried Area (dashed red line) \u2013 the portion of buried area contributed by polar residues.',
          'Non-Polar Buried Area (dotted green line) \u2013 the portion contributed by non-polar residues.'
        ]
      },
      {
        heading: 'How to read it',
        paragraphs: [
          'A stable total BSA across frames indicates a structurally stable interface. Divergence between polar and non-polar traces can indicate shifts in interface character, such as a growing hydrophobic core or an emerging polar patch.',
          'Toggle \"Mean \u00B1 Std Dev\" to display shaded bands around each line showing the average range. The legend includes the numerical mean and standard deviation values.',
          'Toggling \"Show Percentages\" switches the y-axis from absolute \u00C5\u00B2 values to the relative percentage contribution of each series.'
        ]
      },
      {
        heading: 'Controls',
        items: [
          'Mean \u00B1 Std Dev toggle \u2013 shows or hides the shaded standard deviation bands, giving a quick visual sense of variability.',
          'Show Percentages toggle \u2013 switches between absolute buried area values (\u00C5\u00B2) and relative proportions (%).'
        ]
      }
    ]
  },
  {
    id: 'chart-conserved-islands',
    title: 'Conserved Islands',
    description: [
      'Conserved Islands are clusters of residues that maintain persistent interactions across the trajectory. Rather than looking at pairs in isolation, this view groups spatially connected residues into islands, giving a higher-level picture of the stable core(s) of the interface.',
      'Integrated with the MolStar 3D viewer, you can highlight selected islands or pairs directly on the molecular structure to see their spatial arrangement.'
    ],
    image: IMG + 'screenshots/conserved-islands.png',
    imageAlt: 'Conserved islands list with bipartite graph visualization',
    subsections: [
      {
        heading: 'What it shows',
        paragraphs: [
          'An island is a connected component of residue pairs that meet the chosen conservation threshold. Each island card lists its residues, the chains involved, and provides a mini bipartite graph (or table) of the internal pairs. Conservation bars indicate how frequently each contact persists.'
        ]
      },
      {
        heading: 'View modes',
        paragraphs: [
          'Two highlight modes are available via radio card buttons above the list:'
        ],
        items: [
          'Conserved Islands \u2013 displays each island as a card. Toggle between a graph view (SVG bipartite network) and a tabular view (residue, chain, residue number, and connected neighbours). Click an island to highlight all its residues in the 3D viewer using ball-and-stick representation.',
          'Most Conserved Pairs \u2013 a sortable, searchable table listing individual residue pairs ranked by their conservation percentage. Features checkboxes, conservation bars, and frame counts. Clicking a pair highlights those specific residues in the 3D viewer.'
        ]
      },
      {
        heading: '3D Visualisation',
        paragraphs: [
          'The MolStar viewer sits above the list. When you select an island or pair, the corresponding residues are highlighted on the 3D structure. In Islands mode, the representation is ball-and-stick to show the complete connectivity. In Pairs mode, it is a selection-based highlight.',
          'Clicking the same item again clears the selection.'
        ],
        image: IMG + 'screenshots/conserved-islands-selection.png',
        imageAlt: 'Conserved islands highlighted on the 3D MolStar viewer'
      },
      {
        heading: 'Controls',
        items: [
          'Pair Conservation Threshold slider \u2013 filters which pairs and islands appear. Raise the threshold to see only the most persistent networks; lower it to include transient contacts.'
        ]
      }
    ]
  },
  {
    id: 'chart-conservation-analysis',
    title: 'Conservation Analysis',
    description: [
      'The Conservation Analysis panel provides quantitative summary metrics about the stability of the interface. It appears at the bottom of each chart page and distills the full trajectory into two key numbers and three ranked lists.'
    ],
    image: IMG + 'screenshots/conservation-analysis.png',
    imageAlt: 'Conservation analysis panel showing CR, CA, and top-ranked interaction metrics',
    subsections: [
      {
        heading: 'What it shows',
        paragraphs: [
          'Two primary metrics are displayed as large summary cards:'
        ],
        items: [
          'CR (Conserved Residue count) \u2013 the number of unique residue pairs that appear in at least the specified percentage of trajectory frames. The subscript indicates the active pair conservation threshold (e.g. CR_{50} at 50%).',
          'CA (Conserved Atomic interactions) \u2013 the number of pair\u2013type combinations (e.g., A-LYS8 \u2013 B-ASP45 via H-bond) that meet the type conservation threshold.'
        ]
      },
      {
        heading: 'Insight rankings',
        paragraphs: [
          'Three ranked cards provide deeper insight into the most significant contacts:'
        ],
        items: [
          'Most Conserved Pairs \u2013 residue pairs ranked by their average conservation across all interaction types. The top 3 are shown with frame counts and coloured interaction type tags. Click the \"+N more\" button for the full list.',
          'Longest Conserved Stretch \u2013 pairs ranked by the maximum number of consecutive frames with any interaction maintained. This highlights contacts that persist without interruption, even if their overall frequency is moderate.',
          'Most Conserved Types \u2013 interaction types ranked by their average conservation across all pairs. Reveals which molecular forces dominate the interface.'
        ]
      },
      {
        heading: 'How to read it',
        paragraphs: [
          'Together these metrics let you quickly assess interface quality. A high CR with a high CA and long consecutive stretches indicates a tight, stable interface. A large discrepancy between CR and CA may suggest many pairs interact, but only through a narrow range of interaction types. The coloured type tags are consistent with the rest of the application\u2014hover for the exact conservation percentage.'
        ]
      }
    ]
  }
]

const tabs = [
  {
    id: 'usage',
    label: 'Usage',
    icon: '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 20h9"/><path d="M16.5 3.5a2.12 2.12 0 013 3L7 19l-4 1 1-4L16.5 3.5z"/></svg>',
    sections: usageSections
  },
  {
    id: 'charts',
    label: 'Charts',
    icon: '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18"/><path d="M9 21V9"/></svg>',
    sections: chartsSections
  },
  {
    id: 'interactions',
    label: 'Interactions',
    icon: '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="8" cy="12" r="4"/><circle cx="16" cy="12" r="4"/></svg>',
    sections: interactionSections
  },
  {
    id: 'legends',
    label: 'Legends',
    icon: '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>',
    sections: legendsSections
  }
]

function switchTab(tabId) {
  activeTab.value = tabId
  sidebarOpen.value = false
  router.replace({ query: { tab: tabId }, hash: '' })
  nextTick(() => {
    setupObserver()
    window.scrollTo({ top: 0, behavior: 'smooth' })
  })
}

function scrollToSection(sectionId) {
  const el = document.getElementById(sectionId)
  if (el) {
    el.scrollIntoView({ behavior: 'smooth' })
    sidebarOpen.value = false
  }
}

function setupObserver() {
  if (observer) observer.disconnect()

  const currentTab = tabs.find(t => t.id === activeTab.value)
  if (!currentTab) return

  const sectionEls = currentTab.sections
    .map(s => document.getElementById(s.id))
    .filter(Boolean)

  if (sectionEls.length === 0) return

  observer = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (entry.isIntersecting) {
          activeSection.value = entry.target.id
        }
      }
    },
    { rootMargin: '-80px 0px -60% 0px', threshold: 0 }
  )

  sectionEls.forEach(el => observer.observe(el))
}

function restoreFromURL() {
  const tabParam = route.query.tab
  if (tabParam && tabs.some(t => t.id === tabParam)) {
    activeTab.value = tabParam
  }
  nextTick(() => {
    setupObserver()
    if (route.hash) {
      const id = route.hash.slice(1)
      const el = document.getElementById(id)
      if (el) {
        setTimeout(() => el.scrollIntoView({ behavior: 'smooth' }), 100)
      }
    }
  })
}

onMounted(() => {
  restoreFromURL()
})

onBeforeUnmount(() => {
  if (observer) observer.disconnect()
})

watch(() => route.query.tab, (newTab) => {
  if (newTab && newTab !== activeTab.value && tabs.some(t => t.id === newTab)) {
    activeTab.value = newTab
    nextTick(() => setupObserver())
  }
})
</script>

<style scoped>
.help-page {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: #f5f5f7;
}

/* ── Header ── */
.page-header {
  padding: 60px 40px 32px;
  text-align: center;
  background: linear-gradient(180deg, #ffffff 0%, #f5f5f7 100%);
}

.page-header h1 {
  font-size: 48px;
  font-weight: 700;
  color: #1d1d1f;
  margin: 0;
  letter-spacing: -0.02em;
}

.subtitle {
  font-size: 21px;
  color: #6e6e73;
  margin: 12px 0 0;
}

/* ── Tab Bar ── */
.docs-tabs {
  display: flex;
  justify-content: center;
  gap: 8px;
  padding: 0 40px 24px;
  background: transparent;
  position: sticky;
  top: 57px;
  z-index: 50;
  background: #f5f5f7;
}

.docs-tab {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 22px;
  font-size: 15px;
  font-weight: 600;
  color: #6e6e73;
  background: #ffffff;
  border: 2px solid #e8e8ed;
  border-radius: 980px;
  cursor: pointer;
  transition: all 0.2s ease;
  font-family: inherit;
}

.docs-tab:hover {
  color: #1d1d1f;
  border-color: #d2d2d7;
  background: #fafafa;
}

.docs-tab.active {
  color: #ffffff;
  background: #1d1d1f;
  border-color: #1d1d1f;
}

.tab-icon {
  display: inline-flex;
  align-items: center;
}

.docs-tab.active .tab-icon :deep(svg) {
  stroke: #ffffff;
}

/* ── Docs Layout ── */
.docs-layout {
  display: flex;
  gap: 0;
  max-width: 1320px;
  margin: 0 auto;
  padding: 0 40px 80px;
  width: 100%;
  position: relative;
}

/* ── Sidebar ── */
.docs-sidebar {
  width: 240px;
  flex-shrink: 0;
  position: sticky;
  top: 120px;
  align-self: flex-start;
  max-height: calc(100vh - 140px);
  overflow-y: auto;
  padding-right: 24px;
  scrollbar-width: thin;
  scrollbar-color: #d2d2d7 transparent;
}

.docs-sidebar::-webkit-scrollbar {
  width: 4px;
}

.docs-sidebar::-webkit-scrollbar-thumb {
  background: #d2d2d7;
  border-radius: 2px;
}

.docs-sidebar-panel {
  display: none;
}

.docs-sidebar-panel.active {
  display: block;
}

.sidebar-heading {
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: #86868b;
  margin: 0 0 12px;
  padding: 0 12px;
}

.sidebar-link {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  font-size: 14px;
  font-weight: 500;
  color: #6e6e73;
  text-decoration: none;
  border-radius: 8px;
  border-left: 3px solid transparent;
  transition: all 0.15s ease;
  margin-bottom: 2px;
}

.sidebar-link:hover {
  color: #1d1d1f;
  background: rgba(0, 0, 0, 0.03);
}

.sidebar-link.active {
  color: #1d1d1f;
  font-weight: 600;
  background: rgba(0, 0, 0, 0.04);
  border-left-color: #1d1d1f;
}

.sidebar-color-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

/* ── Mobile Sidebar ── */
.sidebar-backdrop {
  display: none;
}

.sidebar-toggle {
  display: none;
}

/* ── Content ── */
.docs-content {
  flex: 1;
  min-width: 0;
}

.docs-panel {
  display: none;
}

.docs-panel.active {
  display: block;
}

.docs-section {
  scroll-margin-top: 140px;
  margin-bottom: 32px;
}

.docs-section-card {
  background: #ffffff;
  border-radius: 20px;
  padding: 40px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

/* ── Section Header with color bar ── */
.section-header {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 8px;
}

.section-color-bar {
  width: 4px;
  height: 32px;
  border-radius: 2px;
  flex-shrink: 0;
}

.section-header h2 {
  font-size: 28px;
  font-weight: 600;
  color: #1d1d1f;
  margin: 0;
  letter-spacing: -0.02em;
}

.section-description {
  font-size: 17px;
  line-height: 1.6;
  color: #6e6e73;
  margin: 0 0 20px;
}

.section-description:last-of-type {
  margin-bottom: 28px;
}

/* ── Section Image ── */
.section-image {
  margin: 0 0 28px;
  text-align: center;
  background: #fafafa;
  border: 1px solid #f0f0f2;
  border-radius: 14px;
  padding: 24px;
}

.section-image img {
  max-width: 100%;
  max-height: 340px;
  height: auto;
  object-fit: contain;
  border-radius: 8px;
}

/* ── Subsections ── */
.docs-subsection {
  margin-bottom: 28px;
}

.docs-subsection:last-child {
  margin-bottom: 0;
}

.docs-card-text h3 {
  font-size: 20px;
  font-weight: 600;
  color: #1d1d1f;
  margin: 0 0 12px;
}

.docs-card-text p {
  font-size: 16px;
  line-height: 1.65;
  color: #424245;
  margin: 0 0 12px;
}

.docs-card-text p:last-child {
  margin-bottom: 0;
}

.docs-card-text ul {
  margin: 8px 0 0;
  padding-left: 24px;
}

.docs-card-text li {
  font-size: 16px;
  line-height: 1.65;
  color: #424245;
  margin-bottom: 6px;
}

/* ── Criteria List (ordered) ── */
.criteria-list {
  margin: 12px 0 0;
  padding-left: 24px;
}

.criteria-list li {
  font-size: 15px;
  line-height: 1.7;
  color: #424245;
  margin-bottom: 8px;
  padding-left: 4px;
}

.criteria-list li::marker {
  color: #86868b;
  font-weight: 600;
}


/* ── Status List ── */
.status-list {
  list-style: none;
  margin: 12px 0 0;
  padding: 0;
}

.status-list-item {
  display: flex;
  align-items: baseline;
  gap: 10px;
  padding: 8px 0;
  font-size: 16px;
  line-height: 1.65;
  color: #424245;
  border-bottom: 1px solid #f0f0f2;
}

.status-list-item:last-child {
  border-bottom: none;
}

.status-indicator {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
  position: relative;
  top: 2px;
}

.status-text strong {
  color: #1d1d1f;
}

/* ── References Footer ── */
.section-references {
  margin-top: 0;
  padding-top: 16px;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.ref-label {
  font-size: 13px;
  font-weight: 600;
  color: #86868b;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.ref-link {
  font-size: 13px;
  color: #0071e3;
  text-decoration: none;
  padding: 3px 10px;
  background: #f0f5ff;
  border-radius: 6px;
  transition: background 0.15s ease, color 0.15s ease;
  word-break: break-all;
}

.ref-link:hover {
  background: #dce8ff;
  color: #0056b3;
}

/* ── Media Layout (text + image) ── */
.docs-card-media {
  display: flex;
  align-items: flex-start;
  gap: 32px;
}

.docs-card-media .docs-card-text {
  flex: 1;
  min-width: 0;
}

.docs-card-image {
  flex-shrink: 0;
  width: 340px;
}

.docs-card-image img {
  width: 100%;
  height: auto;
  border-radius: 12px;
  background: #fafafa;
  border: 1px solid #f0f0f2;
}

/* ── Responsive ── */
@media (max-width: 992px) {
  .page-header {
    padding: 40px 24px 24px;
  }

  .page-header h1 {
    font-size: 36px;
  }

  .docs-tabs {
    padding: 0 24px 20px;
    gap: 6px;
    flex-wrap: wrap;
  }

  .docs-tab {
    padding: 8px 16px;
    font-size: 14px;
  }

  .docs-layout {
    padding: 0 24px 60px;
  }

  .docs-sidebar {
    position: fixed;
    top: 0;
    left: 0;
    width: 280px;
    height: 100vh;
    max-height: 100vh;
    background: #ffffff;
    z-index: 200;
    padding: 24px;
    box-shadow: 4px 0 24px rgba(0, 0, 0, 0.12);
    transform: translateX(-100%);
    transition: transform 0.25s ease;
    border-radius: 0;
  }

  .docs-sidebar.open {
    transform: translateX(0);
  }

  .sidebar-backdrop {
    display: block;
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.3);
    z-index: 199;
    animation: fadeIn 0.2s ease;
  }

  .sidebar-toggle {
    display: flex;
    align-items: center;
    justify-content: center;
    position: fixed;
    bottom: 24px;
    left: 24px;
    width: 48px;
    height: 48px;
    background: #1d1d1f;
    color: #ffffff;
    border: none;
    border-radius: 50%;
    cursor: pointer;
    z-index: 198;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
    transition: transform 0.15s ease, background 0.15s ease;
  }

  .sidebar-toggle:hover {
    background: #000000;
    transform: scale(1.05);
  }

  .docs-section-card {
    padding: 28px;
  }

  .docs-card-media {
    flex-direction: column;
  }

  .docs-card-image {
    width: 100%;
    max-width: 400px;
  }

  .section-image img {
    max-height: 260px;
  }
}

@media (max-width: 600px) {
  .docs-tabs {
    gap: 4px;
  }

  .docs-tab {
    padding: 7px 12px;
    font-size: 13px;
    gap: 5px;
  }

  .tab-icon {
    display: none;
  }

  .docs-section-card {
    padding: 20px;
    border-radius: 16px;
  }

  .section-header h2 {
    font-size: 22px;
  }

  .docs-card-text h3 {
    font-size: 18px;
  }

  .section-image {
    padding: 16px;
  }

  .section-image img {
    max-height: 200px;
  }

  .section-references {
    flex-direction: column;
    align-items: flex-start;
  }
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}
</style>
