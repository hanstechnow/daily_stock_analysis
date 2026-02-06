
import React, { useEffect, useState } from 'react';
import { useQuantStore } from '../store/quant';

const QuantPage: React.FC = () => {
  const { 
    strategies, fetchStrategies, toggleStrategy, deleteStrategy, 
    generateStrategy, generatedCode, saveStrategy, clearGeneratedCode, loading 
  } = useQuantStore();

  const [desc, setDesc] = useState('');
  const [newStratName, setNewStratName] = useState('');
  const [showSaveDialog, setShowSaveDialog] = useState(false);

  useEffect(() => {
    fetchStrategies();
  }, []);

  const handleGenerate = () => {
    if (!desc) return;
    generateStrategy(desc);
  };

  const handleSave = async () => {
    if (!newStratName || !generatedCode) return;
    await saveStrategy(newStratName, desc, generatedCode);
    setShowSaveDialog(false);
    clearGeneratedCode();
    setNewStratName('');
    setDesc('');
  };

  return (
    <div className="container mx-auto p-6 max-w-6xl">
      <h1 className="text-3xl font-bold mb-8 text-gray-800">📊 量化策略实验室</h1>
      
      {/* 策略生成区 */}
      <div className="bg-white rounded-xl shadow-sm p-6 mb-8 border border-gray-100">
        <h2 className="text-xl font-semibold mb-4 text-gray-700">💡 AI 策略生成器</h2>
        <div className="flex gap-4 mb-4">
          <input 
            type="text" 
            className="flex-1 p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
            placeholder="用自然语言描述策略，例如：'当MA5金叉MA20且RSI小于70时买入'"
            value={desc}
            onChange={e => setDesc(e.target.value)}
          />
          <button 
            onClick={handleGenerate}
            disabled={loading || !desc}
            className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors font-medium"
          >
            {loading ? '生成中...' : '✨ 生成代码'}
          </button>
        </div>

        {generatedCode && (
          <div className="mt-4 animate-in fade-in slide-in-from-top-2">
            <div className="bg-gray-900 rounded-lg overflow-hidden">
              <div className="flex justify-between items-center px-4 py-2 bg-gray-800 border-b border-gray-700">
                <span className="text-xs text-gray-400 font-mono">Generated Strategy.py</span>
                <div className="flex gap-2">
                  <button onClick={() => clearGeneratedCode()} className="text-xs text-gray-400 hover:text-white">Discard</button>
                  <button 
                    onClick={() => setShowSaveDialog(true)}
                    className="text-xs bg-green-600 text-white px-3 py-1 rounded hover:bg-green-700"
                  >
                    Save Strategy
                  </button>
                </div>
              </div>
              <pre className="p-4 text-sm font-mono text-green-400 overflow-x-auto">
                <code>{generatedCode}</code>
              </pre>
            </div>
            
            {showSaveDialog && (
              <div className="mt-4 flex gap-4 items-center bg-blue-50 p-4 rounded-lg border border-blue-100">
                <input 
                  type="text" 
                  placeholder="给策略起个名字..." 
                  className="flex-1 p-2 border border-blue-200 rounded"
                  value={newStratName}
                  onChange={e => setNewStratName(e.target.value)}
                />
                <button 
                  onClick={handleSave}
                  className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 text-sm"
                >
                  确认保存
                </button>
              </div>
            )}
          </div>
        )}
      </div>

      {/* 策略列表区 */}
      <h2 className="text-2xl font-bold mb-6 text-gray-800">📚 我的策略库</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {strategies.map(strat => (
          <div key={strat.id} className="bg-white rounded-xl shadow-sm border border-gray-200 hover:shadow-md transition-shadow flex flex-col">
            <div className="p-6 flex-1">
              <div className="flex justify-between items-start mb-2">
                <h3 className="font-bold text-lg text-gray-900">{strat.name}</h3>
                <span className={`px-2 py-1 rounded text-xs font-medium ${
                  strat.status === 'active' 
                    ? 'bg-green-100 text-green-800' 
                    : 'bg-gray-100 text-gray-600'
                }`}>
                  {strat.status === 'active' ? '● 运行中' : '○ 已停止'}
                </span>
              </div>
              <p className="text-gray-600 text-sm mb-4 line-clamp-3" title={strat.description}>
                {strat.description}
              </p>
              <div className="text-xs text-gray-400 font-mono mb-4">ID: {strat.id}</div>
            </div>
            
            <div className="px-6 py-4 bg-gray-50 border-t border-gray-100 rounded-b-xl flex justify-between items-center">
              <label className="relative inline-flex items-center cursor-pointer">
                <input 
                  type="checkbox" 
                  className="sr-only peer"
                  checked={strat.status === 'active'}
                  onChange={() => toggleStrategy(strat.id, strat.status === 'active' ? 'inactive' : 'active')}
                />
                <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                <span className="ml-3 text-sm font-medium text-gray-600">启用</span>
              </label>
              
              <button 
                onClick={() => { if(confirm('确定删除该策略吗?')) deleteStrategy(strat.id); }}
                className="text-red-500 hover:text-red-700 text-sm font-medium"
              >
                删除
              </button>
            </div>
          </div>
        ))}

        {strategies.length === 0 && (
          <div className="col-span-full py-12 text-center text-gray-400 bg-gray-50 rounded-xl border border-dashed border-gray-300">
            暂无策略，请在上方生成并添加
          </div>
        )}
      </div>
    </div>
  );
};

export default QuantPage;
