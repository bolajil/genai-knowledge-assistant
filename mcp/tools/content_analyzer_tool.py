from typing import Dict, Any, Sequence
from mcp.server.models import Tool
from mcp.types import TextContent
from pathlib import Path
import os

class ContentAnalyzerTool:
    def __init__(self, index_root_path=None):
        self.name = "content_analyzer"
        self.description = "Analyze your FAISS indexes and provide detailed insights"
        self.index_root = Path(index_root_path) if index_root_path else Path("data/faiss_index")
        
    def get_tool_definition(self) -> Tool:
        return Tool(
            name=self.name,
            description=self.description,
            inputSchema={
                "type": "object",
                "properties": {
                    "index_name": {
                        "type": "string",
                        "description": "Name of the FAISS index to analyze"
                    },
                    "analysis_type": {
                        "type": "string",
                        "enum": ["summary", "statistics", "health", "comparison"],
                        "description": "Type of analysis to perform"
                    }
                },
                "required": ["index_name", "analysis_type"]
            }
        )
    
    async def execute(self, arguments: Dict[str, Any]) -> Sequence[TextContent]:
        try:
            index_name = arguments.get("index_name")
            analysis_type = arguments.get("analysis_type")
            
            if not self._index_exists(index_name):
                return [TextContent(
                    type="text",
                    text=f"❌ Index '{index_name}' not found in {self.index_root}"
                )]
            
            analysis_result = self._perform_analysis(index_name, analysis_type)
            
            return [TextContent(
                type="text", 
                text=analysis_result
            )]
            
        except Exception as e:
            return [TextContent(
                type="text",
                text=f"❌ Content analysis error: {str(e)}"
            )]
    
    def _index_exists(self, index_name: str) -> bool:
        index_path = self.index_root / index_name
        return index_path.exists() and index_path.is_dir()
    
    def _perform_analysis(self, index_name: str, analysis_type: str) -> str:
        index_path = self.index_root / index_name
        
        # Get basic stats
        try:
            file_count = len(list(index_path.glob("*")))
            total_size = sum(f.stat().st_size for f in index_path.glob('*') if f.is_file())
            size_mb = total_size / (1024 * 1024)
            
            # Get file types
            file_extensions = {}
            for file in index_path.glob("*"):
                if file.is_file():
                    ext = file.suffix or "no_extension"
                    file_extensions[ext] = file_extensions.get(ext, 0) + 1
                    
        except Exception as e:
            return f"❌ Error analyzing index: {str(e)}"
        
        if analysis_type == "summary":
            return f"""📊 **Index Summary: {index_name}**

📁 **Location:** `{index_path}`
📄 **Files:** {file_count}
💾 **Size:** {size_mb:.2f} MB
📅 **Last Modified:** {self._get_last_modified(index_path)}

📈 **File Breakdown:**
{self._format_file_breakdown(file_extensions)}

✅ **Status:** {'Healthy' if file_count > 0 else 'Empty'}
            """
        
        elif analysis_type == "statistics":
            return f"""📈 **Detailed Statistics: {index_name}**

🔢 **Storage Metrics:**
- Total files: {file_count}
- Total size: {size_mb:.2f} MB
- Average file size: {(size_mb / file_count):.3f} MB per file
- Largest file: {self._get_largest_file(index_path)}

📊 **Index Health:**
- Status: {'✅ Good' if size_mb > 0 else '⚠️ Empty'}
- Completeness: {'✅ Complete' if file_count >= 3 else '⚠️ Incomplete'}
- Accessibility: ✅ Readable

🔍 **Usage Recommendations:**
{self._get_usage_recommendations(size_mb, file_count)}
            """
        
        elif analysis_type == "health":
            health_score = self._calculate_health_score(file_count, size_mb)
            return f"""🏥 **Health Check: {index_name}**

🎯 **Overall Health Score:** {health_score}/100

✅ **Checks Passed:**
- Index exists and accessible
- Files present: {file_count > 0}
- Reasonable size: {0.1 <= size_mb <= 1000}
- FAISS files detected: {self._has_faiss_files(index_path)}

⚠️ **Warnings:**
{self._get_health_warnings(file_count, size_mb, index_path)}

📋 **Recommendations:**
{self._get_health_recommendations(health_score)}
            """
        
        elif analysis_type == "comparison":
            all_indexes = [d.name for d in self.index_root.iterdir() if d.is_dir()]
            return f"""⚖️ **Index Comparison: {index_name}**

📊 **Current Index Stats:**
- Size: {size_mb:.2f} MB
- Files: {file_count}

🔄 **Compared to Other Indexes:**
{self._compare_with_others(index_name, size_mb, file_count, all_indexes)}

🏆 **Ranking:** {self._get_ranking(index_name, all_indexes)}
            """
    
    def _format_file_breakdown(self, file_extensions: Dict[str, int]) -> str:
        if not file_extensions:
            return "- No files found"
        
        breakdown = []
        for ext, count in sorted(file_extensions.items(), key=lambda x: x[1], reverse=True):
            breakdown.append(f"- {ext}: {count} files")
        return "\n".join(breakdown)
    
    def _get_last_modified(self, index_path: Path) -> str:
        try:
            import datetime
            mtime = max(f.stat().st_mtime for f in index_path.glob('*') if f.is_file())
            return datetime.datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
        except:
            return "Unknown"
    
    def _get_largest_file(self, index_path: Path) -> str:
        try:
            largest = max(index_path.glob('*'), key=lambda f: f.stat().st_size if f.is_file() else 0)
            size = largest.stat().st_size / (1024 * 1024)
            return f"{largest.name} ({size:.2f} MB)"
        except:
            return "Unknown"
    
    def _calculate_health_score(self, file_count: int, size_mb: float) -> int:
        score = 50  # Base score
        
        # File count scoring
        if file_count > 0:
            score += 20
        if file_count >= 3:  # Standard FAISS files
            score += 15
            
        # Size scoring
        if 0.1 <= size_mb <= 1000:
            score += 15
            
        return min(score, 100)
    
    def _has_faiss_files(self, index_path: Path) -> bool:
        faiss_files = ['.faiss', '.pkl']
        return any(
            any(f.suffix == ext for f in index_path.glob('*'))
            for ext in faiss_files
        )
    
    def _get_health_warnings(self, file_count: int, size_mb: float, index_path: Path) -> str:
        warnings = []
        
        if file_count == 0:
            warnings.append("- Index is empty")
        elif file_count < 3:
            warnings.append("- Index may be incomplete (< 3 files)")
            
        if size_mb > 500:
            warnings.append("- Large index size may impact performance")
        elif size_mb < 0.01:
            warnings.append("- Very small index size")
            
        if not self._has_faiss_files(index_path):
            warnings.append("- Missing expected FAISS files")
            
        return "\n".join(warnings) if warnings else "- None detected"
    
    def _get_health_recommendations(self, health_score: int) -> str:
        if health_score >= 80:
            return "- Index is in good condition\n- No immediate action required"
        elif health_score >= 60:
            return "- Consider rebuilding if experiencing issues\n- Monitor performance"
        else:
            return "- Rebuild index recommended\n- Check source documents\n- Verify indexing process"
    
    def _compare_with_others(self, current_name: str, current_size: float, current_files: int, all_indexes: List[str]) -> str:
        if len(all_indexes) <= 1:
            return "- No other indexes to compare with"
        
        comparisons = []
        for other_name in all_indexes:
            if other_name != current_name:
                try:
                    other_path = self.index_root / other_name
                    other_size = sum(f.stat().st_size for f in other_path.glob('*') if f.is_file()) / (1024 * 1024)
                    other_files = len(list(other_path.glob("*")))
                    
                    size_comparison = "larger" if current_size > other_size else "smaller"
                    files_comparison = "more" if current_files > other_files else "fewer"
                    
                    comparisons.append(f"- vs {other_name}: {size_comparison} ({current_size:.1f} vs {other_size:.1f} MB), {files_comparison} files ({current_files} vs {other_files})")
                except:
                    comparisons.append(f"- vs {other_name}: comparison failed")
        
        return "\n".join(comparisons[:3])  # Limit to 3 comparisons
    
    def _get_ranking(self, current_name: str, all_indexes: List[str]) -> str:
        try:
            sizes = []
            for idx_name in all_indexes:
                idx_path = self.index_root / idx_name
                size = sum(f.stat().st_size for f in idx_path.glob('*') if f.is_file()) / (1024 * 1024)
                sizes.append((idx_name, size))
            
            sizes.sort(key=lambda x: x[1], reverse=True)
            rank = next(i for i, (name, _) in enumerate(sizes, 1) if name == current_name)
            
            return f"#{rank} of {len(all_indexes)} (by size)"
        except:
            return "Unable to calculate"
    
    def _get_usage_recommendations(self, size_mb: float, file_count: int) -> str:
        recommendations = []
        
        if size_mb > 100:
            recommendations.append("- Consider splitting large index for better performance")
        if file_count < 3:
            recommendations.append("- Index may need rebuilding")
        if size_mb < 1:
            recommendations.append("- Small index - consider combining with others")
            
        return "\n".join(recommendations) if recommendations else "- Index appears optimally sized"
