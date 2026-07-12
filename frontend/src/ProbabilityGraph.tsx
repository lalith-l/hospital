import { useEffect, useRef } from 'react';
import * as d3 from 'd3';

export interface DiseaseProbability {
  name: string;
  score: number;
}

interface ProbabilityGraphProps {
  data: DiseaseProbability[];
}

export default function ProbabilityGraph({ data }: ProbabilityGraphProps) {
  const d3Container = useRef<SVGSVGElement | null>(null);

  useEffect(() => {
    if (data && d3Container.current) {
      const svg = d3.select(d3Container.current);
      svg.selectAll('*').remove();

      const width = 200;
      const height = 150;
      const margin = { top: 10, right: 10, bottom: 20, left: 60 };

      const innerWidth = width - margin.left - margin.right;
      const innerHeight = height - margin.top - margin.bottom;

      const g = svg.append('g')
        .attr('transform', `translate(${margin.left},${margin.top})`);

      const x = d3.scaleLinear()
        .domain([0, 1])
        .range([0, innerWidth]);

      const y = d3.scaleBand()
        .domain(data.map(d => d.name))
        .range([0, innerHeight])
        .padding(0.2);

      // Y Axis
      g.append('g')
        .call(d3.axisLeft(y).tickSize(0).tickPadding(8))
        .attr('color', 'rgba(255, 255, 255, 0.5)')
        .selectAll('text')
        .attr('font-size', '10px')
        .attr('font-weight', '500')
        .attr('fill', '#9ca3af');

      g.select('.domain').remove();

      // Bars
      const bars = g.selectAll('.bar')
        .data(data, (d: any) => d.name);

      bars.enter().append('rect')
        .attr('class', 'bar')
        .attr('y', d => y(d.name)!)
        .attr('height', y.bandwidth())
        .attr('x', 0)
        .attr('width', 0)
        .attr('fill', 'url(#gradient)')
        .attr('rx', 4)
        .merge(bars as any)
        .transition()
        .duration(800)
        .ease(d3.easeCubicOut)
        .attr('width', d => x(d.score));

      bars.exit().remove();

      // Labels on bars
      const labels = g.selectAll('.label')
        .data(data, (d: any) => d.name);

      labels.enter().append('text')
        .attr('class', 'label')
        .attr('y', d => y(d.name)! + y.bandwidth() / 2)
        .attr('dy', '0.35em')
        .attr('x', 0)
        .attr('fill', 'white')
        .attr('font-size', '10px')
        .attr('font-weight', 'bold')
        .text(d => (d.score * 100).toFixed(0) + '%')
        .merge(labels as any)
        .transition()
        .duration(800)
        .ease(d3.easeCubicOut)
        .attr('x', d => x(d.score) + 4);

      labels.exit().remove();

      // Gradient definition
      const defs = svg.append('defs');
      const gradient = defs.append('linearGradient')
        .attr('id', 'gradient')
        .attr('x1', '0%')
        .attr('y1', '0%')
        .attr('x2', '100%')
        .attr('y2', '0%');

      gradient.append('stop')
        .attr('offset', '0%')
        .attr('stop-color', '#3b82f6'); // tailwind blue-500
      gradient.append('stop')
        .attr('offset', '100%')
        .attr('stop-color', '#8b5cf6'); // tailwind violet-500

    }
  }, [data]);

  if (!data || data.length === 0) return null;

  return (
    <div className="bg-white/5 rounded-lg p-3 border border-white/5 mt-4">
      <p className="text-xs font-semibold text-textMuted uppercase tracking-wider mb-2">Differential Diagnosis</p>
      <svg
        className="d3-component w-full"
        width={200}
        height={150}
        ref={d3Container}
      />
    </div>
  );
}
