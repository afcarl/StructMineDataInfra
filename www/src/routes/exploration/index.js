import React from 'react';
import Exploration from './Exploration';
import Layout from '../../components/Layout';

async function action() {
  const title = 'Network Exploration'
  return {
    chunks: ['exploration'],
    title: title,
    component: (
      <Layout title={title}>
        <Exploration />
      </Layout>
    ),
  };
}

export default action;
