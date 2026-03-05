import React, { useEffect, useState, useCallback } from 'react';
import { candidateService } from '../../services/candidate.service';
import './Resources.css';

interface Resource {
  id: number;
  title: string;
  url: string;
  category: string;
  source: string;
}

interface GapSection {
  topic: string;
  resources: Resource[];
}

const SOURCE_LABELS: Record<string, string> = {
  'full-stack-web-dev': 'Full-Stack Web Dev',
  'computer-science-courses': 'CS Courses',
  'computer-science-readings': 'CS Readings',
  'cs-video-courses': 'CS Video Courses',
  'free-courses': 'Free Courses',
  'ivy-league-courses': 'Ivy League Courses',
  'free-certifications': 'Free Certifications',
  'free-courses-extras': 'Free Courses (Extras)',
  'developer-resources-hub': 'Developer Resources Hub',
};

const PAGE_SIZE = 20;

export default function Resources() {
  // --- browse state ---
  const [resources, setResources] = useState<Resource[]>([]);
  const [categories, setCategories] = useState<string[]>([]);
  const [sources, setSources] = useState<string[]>([]);
  const [selectedCategory, setSelectedCategory] = useState('');
  const [selectedSource, setSelectedSource] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [inputValue, setInputValue] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [totalCount, setTotalCount] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [page, setPage] = useState(1);

  // --- for-you state ---
  const [forYouGaps, setForYouGaps] = useState<GapSection[]>([]);
  const [forYouLoading, setForYouLoading] = useState(true);
  const [forYouExpanded, setForYouExpanded] = useState(true);

  // --- load for-you once ---
  useEffect(() => {
    candidateService.getForYouResources()
      .then((data) => setForYouGaps(data.gaps))
      .catch(() => setForYouGaps([]))
      .finally(() => setForYouLoading(false));
  }, []);

  // --- load browse resources ---
  const fetchResources = useCallback(async (targetPage: number) => {
    setLoading(true);
    setError('');
    try {
      const params: Record<string, string | number> = { page: targetPage, page_size: PAGE_SIZE };
      if (selectedCategory) params.category = selectedCategory;
      if (selectedSource) params.source = selectedSource;
      if (searchQuery) params.q = searchQuery;

      const data = await candidateService.getLearningResources(params);
      setResources(data.resources);
      setTotalCount(data.total_count);
      setTotalPages(data.total_pages);
      setPage(data.page);
      if (categories.length === 0) setCategories(data.categories);
      if (sources.length === 0) setSources(data.sources);
    } catch {
      setError('Failed to load resources. Please try again.');
    } finally {
      setLoading(false);
    }
  }, [selectedCategory, selectedSource, searchQuery]);

  useEffect(() => {
    fetchResources(1);
  }, [selectedCategory, selectedSource, searchQuery]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setSearchQuery(inputValue.trim());
  };

  const handleClearFilters = () => {
    setSelectedCategory('');
    setSelectedSource('');
    setSearchQuery('');
    setInputValue('');
  };

  const handlePageChange = (newPage: number) => {
    fetchResources(newPage);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const hasActiveFilters = selectedCategory || selectedSource || searchQuery;

  return (
    <div className="resources-page">
      <div className="resources-header">
        <h1 className="resources-title">Learning Resources</h1>
    </div>

      {/* For You section */}
      {(forYouLoading || forYouGaps.length > 0) && (
        <div className="for-you-section">
          <div className="for-you-header" onClick={() => setForYouExpanded((v) => !v)}>
            <div className="for-you-title-row">
              <span className="for-you-badge">For You</span>
              <h2 className="for-you-heading">Strengthen Your Weak Areas</h2>
            </div>
            <span className="for-you-toggle">{forYouExpanded ? '▲' : '▼'}</span>
          </div>

          {forYouExpanded && (
            forYouLoading ? (
              <div className="for-you-loading">Analysing your applications...</div>
            ) : (
              <div className="for-you-gaps">
                {forYouGaps.map((gap) => (
                  <div key={gap.topic} className="gap-block">
                    <div className="gap-topic">
                      <span className="gap-icon">⚡</span>
                      {gap.topic}
                    </div>
                    <div className="gap-resources">
                      {gap.resources.map((r) => (
                        <a
                          key={r.id}
                          href={r.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="gap-resource-card"
                        >
                          <span className="gap-resource-source">{SOURCE_LABELS[r.source] || r.source}</span>
                          <span className="gap-resource-title">{r.title}</span>
                          <svg className="gap-resource-arrow" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>
                            <polyline points="15 3 21 3 21 9"/>
                            <line x1="10" y1="14" x2="21" y2="3"/>
                          </svg>
                        </a>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )
          )}
        </div>
      )}

      {/* Browse section */}
      <div className="resources-layout">
        {/* Sidebar */}
        <aside className="resources-sidebar">
          <div className="sidebar-section">
            <h3 className="sidebar-heading">Source</h3>
            <button
              className={`sidebar-item ${!selectedSource ? 'sidebar-item--active' : ''}`}
              onClick={() => setSelectedSource('')}
            >
              All Sources
              <span className="sidebar-count">{totalCount}</span>
            </button>
            {sources.map((src) => (
              <button
                key={src}
                className={`sidebar-item ${selectedSource === src ? 'sidebar-item--active' : ''}`}
                onClick={() => setSelectedSource(selectedSource === src ? '' : src)}
              >
                {SOURCE_LABELS[src] || src}
              </button>
            ))}
          </div>

          <div className="sidebar-section">
            <h3 className="sidebar-heading">Category</h3>
            <button
              className={`sidebar-item ${!selectedCategory ? 'sidebar-item--active' : ''}`}
              onClick={() => setSelectedCategory('')}
            >
              All Categories
            </button>
            {categories.map((cat) => (
              <button
                key={cat}
                className={`sidebar-item ${selectedCategory === cat ? 'sidebar-item--active' : ''}`}
                onClick={() => setSelectedCategory(selectedCategory === cat ? '' : cat)}
                title={cat}
              >
                <span className="sidebar-item-label">{cat}</span>
              </button>
            ))}
          </div>
        </aside>

        {/* Main */}
        <main className="resources-main">
          <form className="resources-search-bar" onSubmit={handleSearch}>
            <input
              type="text"
              className="resources-search-input"
              placeholder="Search by title..."
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
            />
            <button type="submit" className="btn btn--primary resources-search-btn">Search</button>
            {hasActiveFilters && (
              <button type="button" className="btn btn--ghost resources-clear-btn" onClick={handleClearFilters}>
                Clear
              </button>
            )}
          </form>

          {hasActiveFilters && (
            <div className="active-filters">
              {selectedSource && (
                <span className="filter-chip">
                  {SOURCE_LABELS[selectedSource] || selectedSource}
                  <button onClick={() => setSelectedSource('')}>&times;</button>
                </span>
              )}
              {selectedCategory && (
                <span className="filter-chip">
                  {selectedCategory}
                  <button onClick={() => setSelectedCategory('')}>&times;</button>
                </span>
              )}
              {searchQuery && (
                <span className="filter-chip">
                  "{searchQuery}"
                  <button onClick={() => { setSearchQuery(''); setInputValue(''); }}>&times;</button>
                </span>
              )}
              <span className="results-count">{totalCount} results</span>
            </div>
          )}

          {loading && <div className="resources-loading">Loading resources...</div>}
          {error && <div className="resources-error">{error}</div>}
          {!loading && !error && resources.length === 0 && (
            <div className="resources-empty">No resources found for the selected filters.</div>
          )}

          {!loading && !error && resources.length > 0 && (
            <>
              <div className="resources-grid">
                {resources.map((resource) => (
                  <a
                    key={resource.id}
                    href={resource.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="resource-card"
                  >
                    <div className="resource-card-badges">
                      <span className="badge badge--source">{SOURCE_LABELS[resource.source] || resource.source}</span>
                      <span className="badge badge--category">{resource.category}</span>
                    </div>
                    <h4 className="resource-card-title">{resource.title}</h4>
                    <svg className="resource-card-link-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>
                      <polyline points="15 3 21 3 21 9"/>
                      <line x1="10" y1="14" x2="21" y2="3"/>
                    </svg>
                  </a>
                ))}
              </div>

              {/* Pagination */}
              <div className="pagination">
                <button
                  className="pagination-btn"
                  disabled={page <= 1}
                  onClick={() => handlePageChange(page - 1)}
                >
                  &larr; Prev
                </button>
                <div className="pagination-pages">
                  {Array.from({ length: Math.min(7, totalPages) }, (_, i) => {
                    let p: number;
                    if (totalPages <= 7) {
                      p = i + 1;
                    } else if (page <= 4) {
                      p = i + 1;
                    } else if (page >= totalPages - 3) {
                      p = totalPages - 6 + i;
                    } else {
                      p = page - 3 + i;
                    }
                    return (
                      <button
                        key={p}
                        className={`pagination-page ${p === page ? 'pagination-page--active' : ''}`}
                        onClick={() => handlePageChange(p)}
                      >
                        {p}
                      </button>
                    );
                  })}
                </div>
                <button
                  className="pagination-btn"
                  disabled={page >= totalPages}
                  onClick={() => handlePageChange(page + 1)}
                >
                  Next &rarr;
                </button>
                <span className="pagination-info">
                  Page {page} of {totalPages} &middot; {totalCount} total
                </span>
              </div>
            </>
          )}
        </main>
      </div>
    </div>
  );
}
