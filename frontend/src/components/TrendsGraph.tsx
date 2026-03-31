import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';
import { motion } from 'framer-motion';

interface TrendsGraphProps {
  data: any[];
  onYearSelect: (year: number) => void;
  selectedYear?: number | null;
}

const TrendsGraph: React.FC<TrendsGraphProps> = ({ data, onYearSelect, selectedYear }) => {
  if (!data || data.length === 0) return (
    <div className="h-64 flex items-center justify-center text-neutral-500">
      Initializing trend analysis...
    </div>
  );

  // Extract publisher names (keys other than 'year_clean')
  const publishers = Object.keys(data[0]).filter(k => k !== 'year_clean');
  const colors = ['#CA8A04', '#EAB308', '#A16207', '#D97706', '#F59E0B'];

  return (
    <motion.div 
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="h-80 w-full"
    >
      <ResponsiveContainer width="100%" height="100%">
        <LineChart 
          data={data} 
          onClick={(e) => {
            if (e && e.activeLabel) {
              onYearSelect(parseInt(e.activeLabel.toString()));
            }
          }}
          margin={{ top: 10, right: 30, left: 0, bottom: 0 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#262626" vertical={false} />
          <XAxis 
            dataKey="year_clean" 
            stroke="#525252" 
            tick={{ fill: '#525252', fontSize: 12 }}
            axisLine={false}
          />
          <YAxis 
            stroke="#525252" 
            tick={{ fill: '#525252', fontSize: 12 }}
            axisLine={false}
          />
          <Tooltip 
            contentStyle={{ 
              backgroundColor: '#1C1917', 
              border: '1px solid #404040',
              borderRadius: '8px',
              fontSize: '12px'
            }}
            itemStyle={{ color: '#CA8A04' }}
          />
          {publishers.map((pub, idx) => (
            <Line 
              key={pub}
              type="monotone" 
              dataKey={pub} 
              stroke={colors[idx % colors.length]} 
              strokeWidth={selectedYear?.toString() === data[0]?.year_clean ? 4 : 2}
              dot={{ r: 4, fill: colors[idx % colors.length] }}
              activeDot={{ r: 6, stroke: '#fff', strokeWidth: 2 }}
              animationDuration={1500}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </motion.div>
  );
};

export default TrendsGraph;
