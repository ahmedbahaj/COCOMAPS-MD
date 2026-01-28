<template>
  <div class="about-page">
    <!-- Navigation -->
    <nav class="nav-bar">
      <router-link to="/" class="nav-logo">Trajectory Analysis</router-link>
      <div class="nav-links">
        <router-link to="/" class="nav-link">Home</router-link>
        <router-link to="/about" class="nav-link active">About</router-link>
        <router-link to="/references" class="nav-link">References</router-link>
      </div>
    </nav>

    <!-- Header -->
    <header class="page-header">
      <h1>About Trajectory Analysis</h1>
      <p class="subtitle">Understanding Protein-Protein Interface Interactions</p>
    </header>

    <!-- Main Content -->
    <main class="content">
      <div class="container">
        <!-- Introduction -->
        <section class="section">
          <h2>What is Trajectory Analysis?</h2>
          <p>
            Trajectory Analysis is a comprehensive tool for analyzing protein-protein 
            and protein-nucleic acid interfaces across molecular dynamics trajectories. 
            It identifies and classifies atomic interactions at molecular interfaces based 
            on precise geometric criteria.
          </p>
          <p>
            Built on top of <strong>CoCoMaps 2.0</strong> (Contact and Contact Maps), this tool 
            extends the capability to molecular dynamics (MD) trajectories, allowing researchers 
            to study how interface contacts evolve over time and identify conserved interactions 
            across simulation frames.
          </p>
        </section>

        <!-- Interaction Types -->
        <section class="section">
          <h2>Interaction Types</h2>
          <p class="section-intro">
            CoCoMaps identifies 16 distinct types of atomic interactions. Each type is shown 
            with its characteristic color used throughout the application.
          </p>

          <div class="interactions-grid">
            <div 
              v-for="interaction in interactionTypes" 
              :key="interaction.id"
              class="interaction-card"
            >
              <div 
                class="interaction-color" 
                :style="{ backgroundColor: interaction.color }"
              ></div>
              <div class="interaction-info">
                <h3>{{ interaction.label }}</h3>
                <p>{{ interaction.description }}</p>
                <div class="interaction-criteria" v-if="interaction.criteria">
                  <strong>Criteria:</strong> {{ interaction.criteria }}
                </div>
              </div>
              <img 
                v-if="interaction.image"
                :src="interaction.image" 
                :alt="interaction.label"
                class="interaction-image"
              />
            </div>
          </div>
        </section>

        <!-- How It Works -->
        <section class="section">
          <h2>How It Works</h2>
          <div class="workflow-steps">
            <div class="workflow-step">
              <div class="step-number">1</div>
              <h3>Upload PDB</h3>
              <p>Upload a multi-model PDB file containing your MD trajectory frames.</p>
            </div>
            <div class="workflow-step">
              <div class="step-number">2</div>
              <h3>Select Chains</h3>
              <p>Choose two chains to analyze the interface between them.</p>
            </div>
            <div class="workflow-step">
              <div class="step-number">3</div>
              <h3>Analyze</h3>
              <p>CoCoMaps processes each frame and identifies all interfacial contacts.</p>
            </div>
            <div class="workflow-step">
              <div class="step-number">4</div>
              <h3>Explore</h3>
              <p>Visualize interaction trends, conservation matrices, and residue-level details.</p>
            </div>
          </div>
        </section>
      </div>
    </main>

    <!-- Footer -->
    <footer class="footer">
      <p>Trajectory Analysis • Powered by CoCoMaps 2.0 and MDAnalysis</p>
    </footer>
  </div>
</template>

<script setup>
const interactionTypes = [
  {
    id: 'h-bond',
    label: 'H-bonds',
    color: '#2196F3',
    description: 'Hydrogen bonds formed by electrostatic attraction between a hydrogen atom covalently bonded to O or N and an electronegative acceptor.',
    criteria: 'D-A distance ≤ 4.0 Å, θ(D-H-A) > 90°',
    image: 'https://aocdweb.com/BioTools/cocomaps2/static/media/hbonds.8949540840ae74d664e3.png'
  },
  {
    id: 'salt-bridge',
    label: 'Salt-bridges',
    color: '#E91E63',
    description: 'Strong electrostatic attraction between positively charged (Lys, Arg) and negatively charged (Asp, Glu) residues.',
    criteria: 'Distance ≤ 4.5 Å',
    image: 'https://aocdweb.com/BioTools/cocomaps2/static/media/saltbridges.82f1d0d0a1235e7d3307.png'
  },
  {
    id: 'water',
    label: 'Water-mediated contacts',
    color: '#00BCD4',
    description: 'Water molecules acting as bridges between electronegative atoms at the interface.',
    criteria: 'Distance ≤ 4.0 Å',
    image: 'https://aocdweb.com/BioTools/cocomaps2/static/media/watermediated.ea388ed529e06004a4a1.png'
  },
  {
    id: 'ch-on',
    label: 'CH-O/N bonds',
    color: '#8BC34A',
    description: 'Weak attraction between a C-H group and an electronegative O or N acceptor.',
    criteria: 'C-X distance ≤ 4.0 Å, θ(C-H-X) > 110°'
  },
  {
    id: 'ss-bond',
    label: 'S-S bonds (Disulfide)',
    color: '#FFC107',
    description: 'Covalent bonds between sulfur atoms (SG) of Cysteine side chains.',
    criteria: 'Distance ≤ 3.0 Å'
  },
  {
    id: 'halogen',
    label: 'Halogen bonds',
    color: '#9C27B0',
    description: 'Interaction between a halogen (F, Cl, Br, I) and an electronegative atom (O, N, S).',
    criteria: 'Distance within sum of vdW radii, θ₁ > 165°, θ₂ > 120°'
  },
  {
    id: 'metal',
    label: 'Metal-mediated contacts',
    color: '#795548',
    description: 'Metal cations coordinating to electronegative atoms (O, N, S).',
    criteria: 'Distance ≤ 3.2 Å'
  },
  {
    id: 'cation-pi',
    label: 'Cation-π interactions',
    color: '#FF5722',
    description: 'Attraction between a cation (Arg, Lys) and the π-cloud of aromatic rings.',
    criteria: 'Distance ≤ 5.0 Å'
  },
  {
    id: 'anion-pi',
    label: 'Anion-π interactions',
    color: '#F44336',
    description: 'Attraction between an anion (Glu, Asp, phosphate) and an aromatic π-cloud.',
    criteria: 'Distance ≤ 5.0 Å'
  },
  {
    id: 'amino-pi',
    label: 'Amino-π interactions',
    color: '#3F51B5',
    description: 'Interaction between an amino group (Asn, Gln) and an aromatic π-cloud.',
    criteria: 'Distance ≤ 5.0 Å'
  },
  {
    id: 'lone-pair-pi',
    label: 'lp-π interactions',
    color: '#009688',
    description: 'Interaction between a lone pair (O, S, N) and an aromatic π-cloud.',
    criteria: 'Distance ≤ 5.0 Å'
  },
  {
    id: 'pi-pi',
    label: 'π-π stacking',
    color: '#673AB7',
    description: 'Attraction between two aromatic rings (His, Phe, Trp, Tyr or nucleobases).',
    criteria: 'Centroid distance ≤ 5.5 Å'
  },
  {
    id: 'ch-pi',
    label: 'CH-π interactions',
    color: '#4CAF50',
    description: 'Attraction between a C-H group and an aromatic π-cloud.',
    criteria: 'Distance ≤ 4.5 Å'
  },
  {
    id: 'ons-oh-pi',
    label: 'O/N/SH-π interactions',
    color: '#FF9800',
    description: 'Attraction between an N-H, O-H, or S-H group and an aromatic π-cloud.',
    criteria: 'Distance ≤ 4.5 Å'
  },
  {
    id: 'apolar-vdw',
    label: 'Apolar vdW contacts',
    color: '#607D8B',
    description: 'Van der Waals contacts between non-polar atoms.',
    criteria: 'Based on vdW radii + 0.5 Å tolerance'
  },
  {
    id: 'polar-vdw',
    label: 'Polar vdW contacts',
    color: '#9E9E9E',
    description: 'Van der Waals contacts involving polar atoms.',
    criteria: 'Based on vdW radii + 0.5 Å tolerance'
  },
  {
    id: 'proximal',
    label: 'Proximal contacts',
    color: '#BDBDBD',
    description: 'Contacts within the 5 Å cutoff not falling into other specific classes.'
  },
  {
    id: 'clash',
    label: 'Clashes',
    color: '#D32F2F',
    description: 'Contacts shorter than the sum of van der Waals radii, indicating steric overlap.'
  }
]
</script>

<style scoped>
.about-page {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: #f5f5f7;
}

/* Navigation */
.nav-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 40px;
  background: #ffffff;
  border-bottom: 1px solid #e8e8ed;
  position: sticky;
  top: 0;
  z-index: 100;
}

.nav-logo {
  font-size: 20px;
  font-weight: 700;
  color: #1d1d1f;
  text-decoration: none;
}

.nav-links {
  display: flex;
  gap: 32px;
}

.nav-link {
  font-size: 15px;
  font-weight: 500;
  color: #6e6e73;
  text-decoration: none;
  transition: color 0.15s ease;
}

.nav-link:hover,
.nav-link.active {
  color: #1d1d1f;
}

/* Header */
.page-header {
  padding: 60px 40px 40px;
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

/* Content */
.content {
  flex: 1;
  padding: 0 40px 80px;
}

.container {
  max-width: 1000px;
  margin: 0 auto;
}

/* Sections */
.section {
  background: #ffffff;
  border-radius: 20px;
  padding: 40px;
  margin-bottom: 32px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.section h2 {
  font-size: 28px;
  font-weight: 600;
  color: #1d1d1f;
  margin: 0 0 20px;
}

.section p {
  font-size: 17px;
  line-height: 1.6;
  color: #424245;
  margin: 0 0 16px;
}

.section-intro {
  margin-bottom: 32px !important;
}

/* Interactions Grid */
.interactions-grid {
  display: grid;
  gap: 20px;
}

.interaction-card {
  display: flex;
  align-items: flex-start;
  gap: 20px;
  padding: 24px;
  background: #f5f5f7;
  border-radius: 16px;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.interaction-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
}

.interaction-color {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  flex-shrink: 0;
}

.interaction-info {
  flex: 1;
}

.interaction-info h3 {
  font-size: 17px;
  font-weight: 600;
  color: #1d1d1f;
  margin: 0 0 8px;
}

.interaction-info p {
  font-size: 15px;
  line-height: 1.5;
  color: #6e6e73;
  margin: 0;
}

.interaction-criteria {
  font-size: 13px;
  color: #86868b;
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid #e8e8ed;
}

.interaction-image {
  width: 120px;
  height: auto;
  border-radius: 8px;
  flex-shrink: 0;
}

/* Workflow Steps */
.workflow-steps {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 24px;
  margin-top: 32px;
}

.workflow-step {
  text-align: center;
  padding: 24px;
  background: #f5f5f7;
  border-radius: 16px;
}

.step-number {
  width: 48px;
  height: 48px;
  background: #1d1d1f;
  color: #ffffff;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  font-weight: 600;
  margin: 0 auto 16px;
}

.workflow-step h3 {
  font-size: 17px;
  font-weight: 600;
  color: #1d1d1f;
  margin: 0 0 8px;
}

.workflow-step p {
  font-size: 14px;
  color: #6e6e73;
  margin: 0;
}

/* Footer */
.footer {
  padding: 24px 40px;
  text-align: center;
  border-top: 1px solid #e8e8ed;
  background: #ffffff;
}

.footer p {
  margin: 0;
  font-size: 14px;
  color: #86868b;
}

/* Responsive */
@media (max-width: 768px) {
  .nav-bar {
    padding: 16px 24px;
  }

  .nav-links {
    gap: 20px;
  }

  .page-header {
    padding: 40px 24px 32px;
  }

  .page-header h1 {
    font-size: 36px;
  }

  .content {
    padding: 0 24px 60px;
  }

  .section {
    padding: 28px;
  }

  .interaction-card {
    flex-direction: column;
  }

  .interaction-image {
    width: 100%;
    max-width: 200px;
  }

  .workflow-steps {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
